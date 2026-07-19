from enum import StrEnum


class QueueMessageType(StrEnum):
    IMPORT_JOB = "IMPORT_JOB"
    RECIPE_EMBEDDING = "RECIPE_EMBEDDING"
    ACCOUNT_DELETION = "ACCOUNT_DELETION"


class QueueOutboxStatus(StrEnum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
