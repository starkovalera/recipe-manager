import dramatiq

from app.core.config import get_settings
from app.core.dramatiq import broker as _broker  # noqa: F401
from app.users.constants import AccountDeletionProcessingDisposition
from app.users.deletion import process_account_deletion

RETRYABLE_DISPOSITIONS = {
    AccountDeletionProcessingDisposition.WAITING_FOR_IMPORTS,
    AccountDeletionProcessingDisposition.RETRYABLE_FAILURE,
}


class RetryableAccountDeletionTaskError(RuntimeError):
    pass


@dramatiq.actor(max_retries=get_settings().account_deletion_task_max_retries)
def delete_account_task(user_id: str) -> None:
    result = process_account_deletion(user_id)
    if result.disposition in RETRYABLE_DISPOSITIONS:
        raise RetryableAccountDeletionTaskError(f"Account deletion returned retryable disposition {result.disposition.value}.")
