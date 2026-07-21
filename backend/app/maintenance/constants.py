from enum import StrEnum


class MaintenanceOperation(StrEnum):
    PENDING_OUTBOX_RECONCILIATION = "pending_outbox_reconciliation"
    STALE_IMPORT_RECONCILIATION = "stale_import_reconciliation"
    STALE_EMBEDDING_RECONCILIATION = "stale_embedding_reconciliation"
    STALE_RECIPE_DELETION_RECONCILIATION = "stale_recipe_deletion_reconciliation"
    EXPIRED_INVITATION_CLEANUP = "expired_invitation_cleanup"
    STALE_ACCOUNT_DELETION_RECONCILIATION = "stale_account_deletion_reconciliation"
    INTEGRITY_CHECK = "integrity_check"


class MaintenanceProcessingDisposition(StrEnum):
    COMPLETED = "COMPLETED"
    NOOP = "NOOP"
    ANOMALIES_FOUND = "ANOMALIES_FOUND"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
