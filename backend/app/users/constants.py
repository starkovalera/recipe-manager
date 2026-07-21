from enum import StrEnum


class AccountDeletionProcessingDisposition(StrEnum):
    COMPLETED = "COMPLETED"
    NOOP = "NOOP"
    WAITING_FOR_IMPORTS = "WAITING_FOR_IMPORTS"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
