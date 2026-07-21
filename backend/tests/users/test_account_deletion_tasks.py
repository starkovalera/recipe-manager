import pytest

from app.users import tasks
from app.users.constants import AccountDeletionProcessingDisposition
from app.users.deletion import AccountDeletionProcessingResult


def result(disposition: AccountDeletionProcessingDisposition) -> AccountDeletionProcessingResult:
    return AccountDeletionProcessingResult(user_id="user-1", disposition=disposition)


@pytest.mark.parametrize(
    "disposition",
    [
        AccountDeletionProcessingDisposition.COMPLETED,
        AccountDeletionProcessingDisposition.NOOP,
    ],
)
def test_delete_account_task_acknowledges_completed_dispositions(
    monkeypatch,
    disposition: AccountDeletionProcessingDisposition,
) -> None:
    monkeypatch.setattr(tasks, "process_account_deletion", lambda _user_id: result(disposition))

    assert tasks.delete_account_task.fn("user-1") is None


@pytest.mark.parametrize(
    "disposition",
    [
        AccountDeletionProcessingDisposition.WAITING_FOR_IMPORTS,
        AccountDeletionProcessingDisposition.RETRYABLE_FAILURE,
    ],
)
def test_delete_account_task_retries_retryable_dispositions(
    monkeypatch,
    disposition: AccountDeletionProcessingDisposition,
) -> None:
    monkeypatch.setattr(tasks, "process_account_deletion", lambda _user_id: result(disposition))

    with pytest.raises(tasks.RetryableAccountDeletionTaskError, match=disposition.value):
        tasks.delete_account_task.fn("user-1")


def test_delete_account_task_uses_configured_retry_count() -> None:
    assert tasks.delete_account_task.options["max_retries"] == 2
