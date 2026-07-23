# Maintenance Processing

## Contract

P8A/P8B1 provide one strict operation-only queue message shared by the maintenance
Lambda and local CLI:

```json
{"operation":"stale_import_reconciliation"}
```

Extra fields and unknown operations are rejected. The dispatcher has one
registry containing exactly these nine operations:

| Operation | Purpose |
|---|---|
| `pending_outbox_reconciliation` | Dispatch the oldest bounded batch of pending outbox rows. |
| `stale_import_reconciliation` | Recover stale queued/running imports using the central import error policy. |
| `failed_import_artifact_cleanup` | Remove safe retained source/derived artifacts from old terminal failed imports. |
| `orphaned_upload_detection` | Report old user-media objects without durable DB references; never delete. |
| `stale_embedding_reconciliation` | Requeue stale embeddings without calling an embedding provider. |
| `stale_recipe_deletion_reconciliation` | Retry recipes left in `DELETION_PENDING`. |
| `expired_invitation_cleanup` | Revoke expired pending provider invitations and finalize local state. |
| `stale_account_deletion_reconciliation` | Create durable account-deletion intents; never delete accounts directly. |
| `integrity_check` | Report known invariant violations and internal record IDs without changing data. |

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
| `FAILED_IMPORT_ARTIFACT_RETENTION_HOURS` | 720 |
| `ORPHANED_UPLOAD_MIN_AGE_HOURS` | 24 |

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

Integrity checks issue read-only SQL queries for successful imports without a
recipe, incomplete ready embeddings, running embeddings without attempt time,
pending users without deletion time, published outbox rows without publication
time, and foreign recipe cover images. Reports contain only the internal IDs
needed to identify each violation. Anomalies are never repaired.

### Failed import artifacts

Old `FAILED` imports without a created recipe or pending import outbox message
are rechecked under lock. Source/derived prefixes are listed and cleaned outside
the transaction. A fresh locked transaction clears matching source references,
sets `FAILED_ARTIFACTS_REMOVED`, and writes `IMPORT_ARTIFACTS_REMOVED` only when
all safe objects are gone. Unsafe keys and provider/DB failures leave the job
retryable as `FAILED`.

### Orphan detection

The detector traverses every page under `imports/source/`, `imports/derived/`,
and `recipes/media/`, batch-resolves `ImportJobSource` and `RecipeImage`
references, and reports old unreferenced or malformed objects. It never calls
storage deletion.

## Reports

Anomaly/failure reports are UTF-8 JSON objects under
`maintenance/reports/{operation}/{yyyy}/{mm}/{dd}/` in
`StorageLocation.SYSTEM_ARTIFACTS`. Clean runs only emit structured logs. A
required report-write failure changes the operation result to
`RETRYABLE_FAILURE`. Reports exclude source content, URLs, email/auth data,
credentials, bytes, ORM objects, and AI payloads.

## Deferred work

The following remain intentionally deferred:

```text
orphaned_upload_cleanup
temporary_resource_cleanup
maintenance report API/UI
```

EventBridge, queues, IAM, DLQs, packaging, and schedules remain infrastructure
work outside P8A.
