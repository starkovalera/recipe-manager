# Maintenance Processing

## Contract

P8A provides one strict operation-only queue message shared by the maintenance
Lambda and local CLI:

```json
{"operation":"stale_import_reconciliation"}
```

Extra fields and unknown operations are rejected. The dispatcher has one
registry containing exactly these seven operations:

| Operation | Purpose |
|---|---|
| `pending_outbox_reconciliation` | Dispatch the oldest bounded batch of pending outbox rows. |
| `stale_import_reconciliation` | Recover stale queued/running imports using the central import error policy. |
| `stale_embedding_reconciliation` | Requeue stale embeddings without calling an embedding provider. |
| `stale_recipe_deletion_reconciliation` | Retry recipes left in `DELETION_PENDING`. |
| `expired_invitation_cleanup` | Revoke expired pending provider invitations and finalize local state. |
| `stale_account_deletion_reconciliation` | Create durable account-deletion intents; never delete accounts directly. |
| `integrity_check` | Count known invariant violations without changing data. |

Processing returns `COMPLETED`, `NOOP`, `ANOMALIES_FOUND`, or
`RETRYABLE_FAILURE`. Lambda reports only `RETRYABLE_FAILURE`, malformed records,
and unexpected exceptions as partial batch failures. CLI exit codes are `0`
for completed/no-op, `1` for retryable failure, and `2` for anomalies.

## Batches And Thresholds

All operations are bounded by `MAINTENANCE_BATCH_SIZE` (default `100`, allowed
range `1..1000`). Stale thresholds are:

| Setting | Default |
|---|---:|
| `STALE_IMPORT_MINUTES` | 30 |
| `STALE_EMBEDDING_MINUTES` | 30 |
| `STALE_RECIPE_DELETION_MINUTES` | 60 |
| `STALE_ACCOUNT_DELETION_MINUTES` | 60 |

Candidate mutations are rechecked under a row lock. PostgreSQL candidate
selection uses `FOR UPDATE SKIP LOCKED`; SQLite tests keep the same behavior
without depending on PostgreSQL syntax.

## State Transitions

### Outbox

The oldest pending rows are dispatched through the existing publisher. Success
persists `PUBLISHED`; failure leaves the row `PENDING` with attempt metadata.

### Imports

- stale `QUEUED` plus no pending intent: create one import outbox row;
- stale `RUNNING` with attempts remaining: preserve `attempt_count`, clear
  current execution/error/result timestamps through `set_queued_for_retry`,
  record `IMPORT_FAILED` with `STALE_IMPORT_RECOVERY`, and create one outbox row;
- stale `RUNNING` with attempts exhausted: set terminal `FAILED` with
  `IMPORT_PROCESSING_FAILED` / `STALE_IMPORT_RECOVERY`, then create the final
  event and notification;
- terminal, fresh, or already scheduled jobs are unchanged.

### Embeddings

- stale `STALE` plus no pending intent: create one embedding outbox row;
- stale `RUNNING`: set `STALE`, clear the current error, preserve failed
  attempts, record `STALE_REQUEUED` with reason
  `maintenance_stale_recovery`, and create one outbox row;
- inactive recipes and already scheduled embeddings are unchanged;
- maintenance never calls the embedding provider.

### Recipe deletion

The reusable deletion processor snapshots unique media keys and closes its DB
scope before storage calls. It attempts every key. Any storage failure leaves
the recipe `DELETION_PENDING`. After successful storage cleanup, a fresh locked
transaction deletes the still-pending recipe. A database failure also leaves it
pending. Maintenance applies this processor to stale pending recipe IDs.

Recipe deletion uses the configured LOCAL or S3 provider through the shared
storage boundary. S3 missing-object deletes are idempotent success.

### Invitations

Expired `PENDING` invitations are snapshotted, revoked at the authentication
provider outside a DB transaction, and then reloaded and locked. A concurrent
accept/revoke is not overwritten. Provider failure leaves the invitation
pending and returns a retryable result.

### Account deletion

Stale users are selected by `deletion_requested_at`. Users with active imports
or an existing pending deletion intent are skipped. Maintenance atomically
creates an ID-only account-deletion outbox row and dispatches it after commit.
It never invokes account deletion itself.

### Integrity

Integrity checks issue read-only SQL counts for successful imports without a
recipe, incomplete ready embeddings, running embeddings without attempt time,
pending users without deletion time, published outbox rows without publication
time, and foreign recipe cover images. Anomalies are reported but never repaired.

## Deferred P8B

These storage-inventory operations remain intentionally deferred to P8B:

```text
failed_import_artifact_cleanup
orphaned_upload_cleanup
temporary_resource_cleanup
```

EventBridge, queues, IAM, DLQs, packaging, and schedules remain infrastructure
work outside P8A.
