# Maintenance Dispatcher Design

## Scope

P8A adds one operation-only maintenance contract shared by a Lambda adapter
and a local CLI. The active operations are:

```text
pending_outbox_reconciliation
stale_import_reconciliation
stale_embedding_reconciliation
stale_recipe_deletion_reconciliation
expired_invitation_cleanup
stale_account_deletion_reconciliation
integrity_check
```

The following storage-backed cleanup operations remain deferred until P9 adds
S3 and P8B can implement them against the production storage boundary:

```text
failed_import_artifact_cleanup
orphaned_upload_cleanup
temporary_resource_cleanup
```

The delivery order is `P8A -> P9 -> P8B`.

## Contract And Execution

Maintenance messages contain only an operation name. The dispatcher owns one
registry mapping the seven fixed operations to focused functions. Lambda and
CLI adapters use the same registry and explicit processing dispositions.

Every operation processes a bounded batch. Database state transitions and
transactional outbox intents are atomic. Provider, network, and storage calls
run outside database transactions.

## Recovery Boundaries

- Pending outbox messages are republished through the existing outbox boundary.
- Stale imports and embeddings are recovered through their existing lifecycle
  rules without invoking extractors or embedding providers.
- Recipe deletion is extracted into an idempotent processor so maintenance can
  recover recipes left in `DELETION_PENDING`.
- Stale account deletion reconciliation schedules durable deletion intent; it
  never performs account deletion itself.
- Integrity checks are read-only and report anomalies without repairing them.

No maintenance run history or generic service framework is introduced.
