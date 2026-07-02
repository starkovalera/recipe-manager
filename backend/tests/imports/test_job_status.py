from app.core.errors import ErrorCode
from app.imports.job_status import fail_import_job
from app.models import ImportJob, ImportJobStatus


class CapturingStorage:
    def __init__(self):
        self.deleted: list[str] = []

    def delete(self, storage_key: str) -> None:
        self.deleted.append(storage_key)


def test_fail_import_job_sets_terminal_error_and_cleans_storage():
    job = ImportJob(owner_id="user-1", client_id="client-1", client_import_id="import-1", status=ImportJobStatus.RUNNING)
    storage = CapturingStorage()

    fail_import_job(
        job,
        storage,
        saved_storage_keys=["one.jpg", "two.jpg"],
        error_code=ErrorCode.NOT_A_RECIPE,
        error_message="The provided sources do not contain a recipe.",
    )

    assert job.status == ImportJobStatus.FAILED
    assert job.error_code == "NOT_A_RECIPE"
    assert job.error_message == "The provided sources do not contain a recipe."
    assert job.finished_at is not None
    assert storage.deleted == ["one.jpg", "two.jpg"]
