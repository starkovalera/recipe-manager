from enum import StrEnum


class QueueProvider(StrEnum):
    DRAMATIQ = "DRAMATIQ"
    SQS = "SQS"


class StorageProvider(StrEnum):
    LOCAL = "LOCAL"
    S3 = "S3"
