from enum import StrEnum


class MaintenanceOperation(StrEnum):
    # Retry the oldest pending transactional outbox messages.
    PENDING_OUTBOX_RECONCILIATION = "pending_outbox_reconciliation"
    # Recover imports stuck in queued or running states.
    STALE_IMPORT_RECONCILIATION = "stale_import_reconciliation"
    # Remove retained source and derived artifacts from old terminal failed imports.
    FAILED_IMPORT_ARTIFACT_CLEANUP = "failed_import_artifact_cleanup"
    # Detect old storage objects without durable DB references; never delete them.
    ORPHANED_UPLOAD_DETECTION = "orphaned_upload_detection"
    # Requeue stale or running embedding work without calling the embedding provider.
    STALE_EMBEDDING_RECONCILIATION = "stale_embedding_reconciliation"
    # Retry recipes left in deletion-pending state.
    STALE_RECIPE_DELETION_RECONCILIATION = "stale_recipe_deletion_reconciliation"
    # Revoke expired pending invitations and finalize local state safely.
    EXPIRED_INVITATION_CLEANUP = "expired_invitation_cleanup"
    # Create durable deletion intents for stale deletion-pending users.
    STALE_ACCOUNT_DELETION_RECONCILIATION = "stale_account_deletion_reconciliation"
    # Report configured database invariant violations without repairing them.
    INTEGRITY_CHECK = "integrity_check"


class MaintenanceProcessingDisposition(StrEnum):
    COMPLETED = "COMPLETED"
    NOOP = "NOOP"
    ANOMALIES_FOUND = "ANOMALIES_FOUND"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
