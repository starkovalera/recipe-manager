from app.imports.constants import ACTIVE_IMPORT_STATUSES, TERMINAL_IMPORT_STATUSES
from app.models import ImportJobStatus


def test_failed_artifacts_removed_is_terminal_and_inactive() -> None:
    assert ImportJobStatus.FAILED_ARTIFACTS_REMOVED in TERMINAL_IMPORT_STATUSES
    assert ImportJobStatus.FAILED_ARTIFACTS_REMOVED not in ACTIVE_IMPORT_STATUSES
