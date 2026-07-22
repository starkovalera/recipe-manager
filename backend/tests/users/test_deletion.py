from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.constants import AuthProviderType
from app.auth.types import AuthenticatedIdentity, AuthProviderError
from app.db.base import Base
from app.models import ImportJob, ImportJobSource, ImportJobStatus, QueueOutboxMessage, Recipe, RecipeImage, SourceType, User, UserStatus
from app.queueing.constants import QueueMessageType, QueueOutboxStatus
from app.users import deletion as deletion_module, reconcile_deletions
from app.users.constants import AccountDeletionProcessingDisposition
from app.users.deletion import AccountDeletionProcessingResult
from app.storage.constants import StorageLocation


class StubAuthProvider:
    provider = AuthProviderType.CLERK

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.deleted_user_ids: list[str] = []

    def delete_user(self, auth_user_id: str) -> None:
        self.deleted_user_ids.append(auth_user_id)
        if self.error is not None:
            raise self.error


class StubStorage:
    def __init__(self, failing_key: str | None = None) -> None:
        self.failing_key = failing_key
        self.deleted_keys: list[str] = []

    def delete(self, location: StorageLocation, storage_key: str) -> None:
        assert location is StorageLocation.USER_MEDIA
        self.deleted_keys.append(storage_key)
        if storage_key == self.failing_key:
            raise OSError("storage unavailable")


def test_account_deletion_processing_result_is_frozen() -> None:
    result = AccountDeletionProcessingResult(
        user_id="user-1",
        disposition=AccountDeletionProcessingDisposition.NOOP,
    )

    assert [disposition.value for disposition in AccountDeletionProcessingDisposition] == [
        "COMPLETED",
        "NOOP",
        "WAITING_FOR_IMPORTS",
        "RETRYABLE_FAILURE",
    ]
    assert result.user_id == "user-1"
    assert result.disposition is AccountDeletionProcessingDisposition.NOOP
    assert result.failed_storage_key_count == 0
    with pytest.raises(FrozenInstanceError):
        result.user_id = "other"


def setup_deletion(
    monkeypatch,
    tmp_path: Path,
    *,
    provider_error: Exception | None = None,
    failing_key: str | None = None,
    provider_type: AuthProviderType = AuthProviderType.CLERK,
):
    engine = create_engine(f"sqlite:///{tmp_path / 'deletion.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    provider = StubAuthProvider(provider_error)
    provider.provider = provider_type
    storage = StubStorage(failing_key)
    monkeypatch.setattr("app.db.session.SessionLocal", session_factory)
    monkeypatch.setattr(deletion_module, "get_auth_provider", lambda: provider)
    return session_factory, provider, storage


def add_pending_user_with_media(session_factory) -> None:
    with session_factory.begin() as session:
        user = User(
            id="user-1",
            auth_user_id="auth-user",
            email="user@example.test",
            status=UserStatus.DELETION_PENDING,
        )
        recipe = Recipe(id="recipe-1", owner=user, title="Recipe")
        recipe.images.extend(
            [
                RecipeImage(
                    id="image-1",
                    storage_key="shared.jpg",
                    original_name="shared.jpg",
                    mime_type="image/jpeg",
                    size_bytes=10,
                    position=0,
                ),
                RecipeImage(
                    id="image-2",
                    storage_key="recipe.jpg",
                    original_name="recipe.jpg",
                    mime_type="image/jpeg",
                    size_bytes=10,
                    position=1,
                ),
            ]
        )
        job = ImportJob(id="job-1", owner=user, client_id="client-1", status=ImportJobStatus.FAILED)
        job.sources.extend(
            [
                ImportJobSource(id="source-1", type=SourceType.IMAGE, image_storage_key="shared.jpg", position=0),
                ImportJobSource(id="source-2", type=SourceType.IMAGE, image_storage_key="upload.jpg", position=1),
            ]
        )
        session.add(user)


def test_request_account_deletion_atomically_marks_user_pending_and_schedules_outbox(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'request-deletion.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory.begin() as session:
        session.add(User(id="user-1", auth_user_id="auth-user", email="user@example.test"))

    with session_factory() as session:
        result = deletion_module.request_account_deletion(
            session,
            AuthenticatedIdentity(AuthProviderType.CLERK, "auth-user"),
        )

        message = session.get(QueueOutboxMessage, result.outbox_message_id)
        assert result.user.status is UserStatus.DELETION_PENDING
        assert message is not None
        assert message.message_type is QueueMessageType.ACCOUNT_DELETION
        assert message.entity_id == "user-1"
        assert message.status is QueueOutboxStatus.PENDING


def test_request_account_deletion_rolls_back_user_when_outbox_scheduling_fails(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'request-deletion-rollback.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory.begin() as session:
        session.add(User(id="user-1", auth_user_id="auth-user", email="user@example.test"))

    monkeypatch.setattr(
        deletion_module,
        "schedule_outbox_message",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("schedule failed")),
    )
    with session_factory() as session, pytest.raises(RuntimeError, match="schedule failed"):
        deletion_module.request_account_deletion(
            session,
            AuthenticatedIdentity(AuthProviderType.CLERK, "auth-user"),
        )

    with session_factory() as session:
        assert session.get(User, "user-1").status is UserStatus.ACTIVE
        assert session.query(QueueOutboxMessage).count() == 0


def test_process_account_deletion_removes_provider_identity_unique_media_and_user(monkeypatch, tmp_path):
    session_factory, provider, storage = setup_deletion(monkeypatch, tmp_path)
    add_pending_user_with_media(session_factory)

    result = deletion_module.process_account_deletion("user-1", storage=storage)

    assert result == AccountDeletionProcessingResult(
        user_id="user-1",
        disposition=AccountDeletionProcessingDisposition.COMPLETED,
    )
    assert provider.deleted_user_ids == ["auth-user"]
    assert storage.deleted_keys == ["recipe.jpg", "shared.jpg", "upload.jpg"]
    with session_factory() as session:
        assert session.get(User, "user-1") is None


def test_process_account_deletion_stops_before_storage_when_provider_fails(monkeypatch, tmp_path):
    session_factory, provider, storage = setup_deletion(
        monkeypatch,
        tmp_path,
        provider_error=AuthProviderError("provider unavailable"),
    )
    add_pending_user_with_media(session_factory)

    result = deletion_module.process_account_deletion("user-1", storage=storage)

    assert result == AccountDeletionProcessingResult(
        user_id="user-1",
        disposition=AccountDeletionProcessingDisposition.RETRYABLE_FAILURE,
    )
    assert provider.deleted_user_ids == ["auth-user"]
    assert storage.deleted_keys == []
    with session_factory() as session:
        assert session.get(User, "user-1").status is UserStatus.DELETION_PENDING


def test_process_account_deletion_preserves_database_when_storage_fails(monkeypatch, tmp_path):
    session_factory, provider, storage = setup_deletion(monkeypatch, tmp_path, failing_key="shared.jpg")
    add_pending_user_with_media(session_factory)

    result = deletion_module.process_account_deletion("user-1", storage=storage)

    assert result == AccountDeletionProcessingResult(
        user_id="user-1",
        disposition=AccountDeletionProcessingDisposition.RETRYABLE_FAILURE,
        failed_storage_key_count=1,
    )
    assert provider.deleted_user_ids == ["auth-user"]
    assert storage.deleted_keys == ["recipe.jpg", "shared.jpg", "upload.jpg"]
    with session_factory() as session:
        assert session.get(User, "user-1").status is UserStatus.DELETION_PENDING


def test_process_account_deletion_retries_provider_mismatch(monkeypatch, tmp_path):
    session_factory, provider, storage = setup_deletion(
        monkeypatch,
        tmp_path,
        provider_type="OTHER",
    )
    add_pending_user_with_media(session_factory)

    result = deletion_module.process_account_deletion("user-1", storage=storage)

    assert result.disposition is AccountDeletionProcessingDisposition.RETRYABLE_FAILURE
    assert result.failed_storage_key_count == 0
    assert provider.deleted_user_ids == []
    assert storage.deleted_keys == []
    with session_factory() as session:
        assert session.get(User, "user-1").status is UserStatus.DELETION_PENDING


def test_process_account_deletion_retries_storage_factory_failure(monkeypatch, tmp_path, caplog):
    session_factory, provider, _storage = setup_deletion(monkeypatch, tmp_path)
    add_pending_user_with_media(session_factory)
    monkeypatch.setattr(
        deletion_module,
        "get_storage_service",
        lambda: (_ for _ in ()).throw(RuntimeError("S3 account-deletion storage is not implemented yet.")),
        raising=False,
    )

    result = deletion_module.process_account_deletion("user-1")

    assert result.disposition is AccountDeletionProcessingDisposition.RETRYABLE_FAILURE
    assert result.failed_storage_key_count == 0
    assert provider.deleted_user_ids == ["auth-user"]
    assert "auth-user" not in caplog.text
    assert "user@example.test" not in caplog.text
    with session_factory() as session:
        assert session.get(User, "user-1").status is UserStatus.DELETION_PENDING


def test_process_account_deletion_retries_final_database_failure(monkeypatch, tmp_path):
    session_factory, provider, storage = setup_deletion(monkeypatch, tmp_path)
    add_pending_user_with_media(session_factory)
    monkeypatch.setattr(
        deletion_module,
        "_delete_pending_user",
        lambda _user_id: (_ for _ in ()).throw(RuntimeError("database unavailable")),
        raising=False,
    )

    result = deletion_module.process_account_deletion("user-1", storage=storage)

    assert result.disposition is AccountDeletionProcessingDisposition.RETRYABLE_FAILURE
    assert provider.deleted_user_ids == ["auth-user"]
    assert storage.deleted_keys == ["recipe.jpg", "shared.jpg", "upload.jpg"]
    with session_factory() as session:
        assert session.get(User, "user-1").status is UserStatus.DELETION_PENDING


def test_process_account_deletion_returns_noop_when_concurrent_worker_finishes(monkeypatch, tmp_path):
    _session_factory, provider, storage = setup_deletion(monkeypatch, tmp_path)
    add_pending_user_with_media(_session_factory)
    monkeypatch.setattr(deletion_module, "_delete_pending_user", lambda _user_id: False, raising=False)

    result = deletion_module.process_account_deletion("user-1", storage=storage)

    assert result.disposition is AccountDeletionProcessingDisposition.NOOP
    assert provider.deleted_user_ids == ["auth-user"]
    assert storage.deleted_keys == ["recipe.jpg", "shared.jpg", "upload.jpg"]


def test_delete_pending_user_locks_candidate_for_update(monkeypatch) -> None:
    class CapturingSession:
        statement = None

        def scalar(self, statement):
            self.statement = statement
            return None

    session = CapturingSession()

    @contextmanager
    def session_context():
        yield session

    monkeypatch.setattr(deletion_module, "db_session", session_context)

    assert deletion_module._delete_pending_user("user-1") is False
    assert session.statement is not None
    assert session.statement._for_update_arg is not None


def test_process_account_deletion_completes_after_partial_cleanup_retry(monkeypatch, tmp_path):
    session_factory, provider, storage = setup_deletion(monkeypatch, tmp_path, failing_key="shared.jpg")
    add_pending_user_with_media(session_factory)

    first = deletion_module.process_account_deletion("user-1", storage=storage)
    storage.failing_key = None
    second = deletion_module.process_account_deletion("user-1", storage=storage)
    third = deletion_module.process_account_deletion("user-1", storage=storage)

    assert first.disposition is AccountDeletionProcessingDisposition.RETRYABLE_FAILURE
    assert first.failed_storage_key_count == 1
    assert second.disposition is AccountDeletionProcessingDisposition.COMPLETED
    assert third.disposition is AccountDeletionProcessingDisposition.NOOP
    assert provider.deleted_user_ids == ["auth-user", "auth-user"]
    assert storage.deleted_keys == [
        "recipe.jpg",
        "shared.jpg",
        "upload.jpg",
        "recipe.jpg",
        "shared.jpg",
        "upload.jpg",
    ]


def test_process_account_deletion_ignores_non_pending_or_missing_user(monkeypatch, tmp_path):
    session_factory, provider, _storage = setup_deletion(monkeypatch, tmp_path)
    with session_factory.begin() as session:
        session.add(User(id="active-user", auth_user_id="auth-user", email="user@example.test"))
    monkeypatch.setattr(
        deletion_module,
        "get_storage_service",
        lambda: (_ for _ in ()).throw(AssertionError("storage must not be resolved")),
    )

    active = deletion_module.process_account_deletion("active-user")
    missing = deletion_module.process_account_deletion("missing-user")

    assert active == AccountDeletionProcessingResult(
        user_id="active-user",
        disposition=AccountDeletionProcessingDisposition.NOOP,
    )
    assert missing == AccountDeletionProcessingResult(
        user_id="missing-user",
        disposition=AccountDeletionProcessingDisposition.NOOP,
    )
    assert provider.deleted_user_ids == []


def test_process_account_deletion_waits_for_active_imports(monkeypatch, tmp_path):
    session_factory, provider, _storage = setup_deletion(monkeypatch, tmp_path)
    with session_factory.begin() as session:
        user = User(
            id="user-1",
            auth_user_id="auth-user",
            email="user@example.test",
            status=UserStatus.DELETION_PENDING,
        )
        user.import_jobs.append(ImportJob(id="job-1", client_id="client-1"))
        session.add(user)
    monkeypatch.setattr(
        deletion_module,
        "get_storage_service",
        lambda: (_ for _ in ()).throw(AssertionError("storage must not be resolved")),
    )

    result = deletion_module.process_account_deletion("user-1")

    assert result == AccountDeletionProcessingResult(
        user_id="user-1",
        disposition=AccountDeletionProcessingDisposition.WAITING_FOR_IMPORTS,
    )
    assert provider.deleted_user_ids == []
    with session_factory() as session:
        assert session.get(User, "user-1").status is UserStatus.DELETION_PENDING


def test_requeue_pending_account_deletions_schedules_and_dispatches_only_pending_users(monkeypatch, tmp_path):
    session_factory, _provider, _storage = setup_deletion(monkeypatch, tmp_path)
    with session_factory.begin() as session:
        session.add_all(
            [
                User(
                    id="pending-user",
                    auth_user_id="pending-auth-user",
                    email="pending@example.test",
                    status=UserStatus.DELETION_PENDING,
                ),
                User(
                    id="pending-user-2",
                    auth_user_id="pending-auth-user-2",
                    email="pending-2@example.test",
                    status=UserStatus.DELETION_PENDING,
                ),
                User(id="active-user", auth_user_id="active-auth-user", email="active@example.test"),
            ]
        )
    dispatched: list[tuple[str, str]] = []

    def assert_committed_and_dispatch(message_id: str) -> bool:
        with session_factory() as session:
            message = session.get(QueueOutboxMessage, message_id)
            assert message is not None
            assert message.message_type is QueueMessageType.ACCOUNT_DELETION
            assert message.status is QueueOutboxStatus.PENDING
            assert session.query(QueueOutboxMessage).count() == 2
            dispatched.append((message.entity_id, message.id))
        return True

    monkeypatch.setattr(deletion_module, "dispatch_outbox_message", assert_committed_and_dispatch, raising=False)

    failed_user_ids = deletion_module.requeue_pending_account_deletions()

    assert [user_id for user_id, _message_id in dispatched] == ["pending-user", "pending-user-2"]
    assert failed_user_ids == []
    with session_factory() as session:
        messages = session.query(QueueOutboxMessage).all()
        assert {message.id for message in messages} == {message_id for _user_id, message_id in dispatched}


def test_requeue_pending_account_deletions_reports_publish_failures(monkeypatch, tmp_path):
    session_factory, _provider, _storage = setup_deletion(monkeypatch, tmp_path)
    with session_factory.begin() as session:
        session.add(
            User(
                id="pending-user",
                auth_user_id="pending-auth-user",
                email="pending@example.test",
                status=UserStatus.DELETION_PENDING,
            )
        )
    dispatched_message_ids: list[str] = []
    monkeypatch.setattr(
        deletion_module,
        "dispatch_outbox_message",
        lambda message_id: dispatched_message_ids.append(message_id) or False,
        raising=False,
    )

    assert deletion_module.requeue_pending_account_deletions() == ["pending-user"]
    assert len(dispatched_message_ids) == 1
    with session_factory() as session:
        message = session.get(QueueOutboxMessage, dispatched_message_ids[0])
        assert message is not None
        assert message.entity_id == "pending-user"
        assert message.status is QueueOutboxStatus.PENDING


def test_reconcile_deletions_exit_code_reflects_publish_failures(monkeypatch):
    monkeypatch.setattr(reconcile_deletions, "requeue_pending_account_deletions", lambda: [])
    assert reconcile_deletions.main() == 0

    monkeypatch.setattr(reconcile_deletions, "requeue_pending_account_deletions", lambda: ["user-1"])
    assert reconcile_deletions.main() == 1
