from app.models import ImportJobStatus

IMPORT_LOG_COMPONENT = "recipes.import"
IMPORT_VIDEO_LOG_COMPONENT = "recipes.import.video"

SUPPORTED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/webp"}
ACTIVE_IMPORT_STATUSES = {ImportJobStatus.QUEUED, ImportJobStatus.RUNNING}
TERMINAL_IMPORT_STATUSES = {
    ImportJobStatus.SUCCEEDED,
    ImportJobStatus.SUCCEEDED_WITH_FLAGS,
    ImportJobStatus.FAILED,
    ImportJobStatus.CANCELLED,
}
