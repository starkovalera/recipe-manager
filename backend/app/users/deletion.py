import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access.queries import list_active_superadmin_ids_for_update
from app.access.rules import can_delete_user
from app.auth.constants import AuthProviderType
from app.auth.current_user import ensure_user_is_active
from app.auth.provider import get_auth_provider
from app.auth.types import AuthenticatedIdentity, AuthProviderError
from app.core.config import get_settings
from app.core.errors import LastActiveSuperadminError, UserNotProvisionedError
from app.core.logging import log_error, log_info
from app.db.session import db_session, db_transaction
from app.imports.constants import ACTIVE_IMPORT_STATUSES
from app.imports.queries import count_import_jobs_by_statuses
from app.models import ImportJob, ImportJobSource, Recipe, RecipeImage, User, UserStatus
from app.queueing.constants import QueueMessageType
from app.queueing.outbox import dispatch_outbox_message, schedule_outbox_message
from app.storage.local import LocalStorageService
from app.users.queries import get_user_by_auth_identity_for_update, list_user_ids_by_status

logger = logging.getLogger(__name__)


class AccountDeletionStorageError(Exception):
    def __init__(self, failed_storage_keys: list[str]) -> None:
        self.failed_storage_keys = failed_storage_keys
        super().__init__("Account media cleanup failed.")


class AccountDeletionActiveImportError(Exception):
    pass


@dataclass(frozen=True)
class AccountDeletionContext:
    user_id: str
    auth_provider: AuthProviderType
    auth_user_id: str | None
    storage_keys: tuple[str, ...]


@dataclass(frozen=True)
class AccountDeletionRequest:
    user: User
    outbox_message_id: str


def request_account_deletion(session: Session, identity: AuthenticatedIdentity) -> AccountDeletionRequest:
    with db_transaction(session):
        user = get_user_by_auth_identity_for_update(session, identity.auth_provider, identity.auth_user_id)
        if user is None:
            raise UserNotProvisionedError()
        if user.status is not UserStatus.DELETION_PENDING:
            ensure_user_is_active(user)
            active_superadmin_ids = list_active_superadmin_ids_for_update(session)
            if not can_delete_user(user, len(active_superadmin_ids)):
                raise LastActiveSuperadminError()
            user.status = UserStatus.DELETION_PENDING
            user.deletion_requested_at = datetime.now(timezone.utc)
        outbox_message = schedule_outbox_message(
            session,
            QueueMessageType.ACCOUNT_DELETION,
            user.id,
        )
    return AccountDeletionRequest(
        user=user,
        outbox_message_id=outbox_message.id,
    )


def _load_account_deletion_context(session: Session, user_id: str) -> AccountDeletionContext | None:
    user = session.get(User, user_id)
    if user is None or user.status is not UserStatus.DELETION_PENDING:
        return None
    if count_import_jobs_by_statuses(session, user_id, ACTIVE_IMPORT_STATUSES):
        raise AccountDeletionActiveImportError("Account deletion is waiting for active imports.")
    recipe_storage_keys = session.scalars(
        select(RecipeImage.storage_key).join(Recipe, RecipeImage.recipe_id == Recipe.id).where(Recipe.owner_id == user_id)
    ).all()
    import_storage_keys = session.scalars(
        select(ImportJobSource.image_storage_key)
        .join(ImportJob)
        .where(ImportJob.owner_id == user_id, ImportJobSource.image_storage_key.is_not(None))
    ).all()
    return AccountDeletionContext(
        user_id=user.id,
        auth_provider=user.auth_provider,
        auth_user_id=user.auth_user_id,
        storage_keys=tuple(sorted(set(recipe_storage_keys) | set(import_storage_keys))),
    )


def process_account_deletion(user_id: str) -> None:
    with db_session() as session:
        context = _load_account_deletion_context(session, user_id)
    if context is None:
        return

    if context.auth_user_id is not None:
        provider = get_auth_provider()
        if provider.provider is not context.auth_provider:
            raise AuthProviderError("Authentication provider does not match the user identity.")
        provider.delete_user(context.auth_user_id)

    storage = LocalStorageService(get_settings().upload_dir)
    failed_storage_keys: list[str] = []
    for storage_key in context.storage_keys:
        try:
            storage.delete(storage_key)
        except Exception as error:
            failed_storage_keys.append(storage_key)
            log_error(
                logger,
                "Account media cleanup failed.",
                user_id=user_id,
                storage_key=storage_key,
                error=repr(error),
            )
    if failed_storage_keys:
        raise AccountDeletionStorageError(failed_storage_keys)

    with db_session() as session:
        user = session.get(User, user_id)
        if user is None or user.status is not UserStatus.DELETION_PENDING:
            return
        session.delete(user)
    log_info(logger, "Account deletion completed.", user_id=user_id)


def requeue_pending_account_deletions() -> list[str]:
    with db_session() as session:
        user_ids = list_user_ids_by_status(session, UserStatus.DELETION_PENDING)
        scheduled = [
            (
                user_id,
                schedule_outbox_message(
                    session,
                    QueueMessageType.ACCOUNT_DELETION,
                    user_id,
                ).id,
            )
            for user_id in user_ids
        ]

    failed_user_ids = [user_id for user_id, message_id in scheduled if not dispatch_outbox_message(message_id)]
    log_info(
        logger,
        "Pending account deletion tasks republished.",
        pending_user_count=len(user_ids),
        publish_failure_count=len(failed_user_ids),
        failed_user_ids=failed_user_ids,
    )
    return failed_user_ids
