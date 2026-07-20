from dataclasses import dataclass
from enum import StrEnum


class ImportProcessingDisposition(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    NOOP = "NOOP"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"


@dataclass(frozen=True)
class ImportProcessingResult:
    import_job_id: str
    disposition: ImportProcessingDisposition
    detailed_error_code: str | None = None
