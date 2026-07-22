# Account-deletion Processing

## Durable user lifecycle

Account deletion starts by durably changing the local user to `DELETION_PENDING`
and scheduling an ID-only outbox message. There is no terminal deletion-failed
user status. The user remains pending until cleanup completes and the row is
physically deleted.

## Queue message contract

The account-deletion queue carries only `{"userId":"<internal-user-id>"}`.
The contract rejects blank IDs and extra fields. Processing does not depend on a
frontend session, access token, email address, or authentication-provider ID in
the queue message.

## Processing dispositions

| Disposition | User state | Transport action |
|---|---|---|
| `COMPLETED` | local user deleted | acknowledge |
| `NOOP` | missing or not pending | acknowledge |
| `WAITING_FOR_IMPORTS` | `DELETION_PENDING` | retry |
| `RETRYABLE_FAILURE` | `DELETION_PENDING` | retry |

The user table has no account-deletion attempt counter. Delivery attempts are a
transport concern.

## Processing order

Each execution:

1. loads a snapshot of the pending user's provider identity and unique media
   storage keys;
2. returns `WAITING_FOR_IMPORTS` while owned imports are queued or running;
3. deletes the external identity when one exists;
4. attempts every media deletion;
5. physically deletes the still-pending local user in a final transaction.

The final local delete cascades through user-owned domain data only after all
external cleanup succeeds.

## State between retries

Provider, storage, or final database failure returns `RETRYABLE_FAILURE` and
leaves the local user `DELETION_PENDING`. Successful external side effects are
not rolled back. A later execution repeats the idempotent operations and uses a
fresh inventory from the database.

## Active-import waiting

Queued or running imports cause `WAITING_FOR_IMPORTS`. Provider and storage
cleanup do not start while active imports exist, so those workers cannot create
new user-owned data during deletion.

## Provider idempotency and Clerk 404

Authentication-provider deletion must be idempotent. For Clerk, a provider
`404` means the identity is already absent and is treated as success. Other
provider errors are retryable.

## Storage inventory and partial cleanup

The processor builds a unique inventory from owned `RecipeImage` and
`ImportJobSource` rows and attempts every key even when one deletion fails.
Failed-key counts may be logged and returned, but storage keys are not included
in aggregate Lambda logs. A partial cleanup keeps the local user pending; an
already-missing object must be an idempotent storage success.

## Final database deletion

The final transaction locks and deletes only a user still in
`DELETION_PENDING`. A concurrent delivery that finds the user missing or no
longer pending returns `NOOP`. A database failure returns `RETRYABLE_FAILURE`.

## Duplicate delivery

Duplicate delivery is expected. Missing or non-pending users are acknowledged
as `NOOP`. Provider deletion and storage deletion must tolerate resources that
were removed by an earlier execution.

## SQS retry and DLQ behavior

The Lambda uses partial batch responses. `COMPLETED` and `NOOP` are
acknowledged; `WAITING_FOR_IMPORTS`, `RETRYABLE_FAILURE`, malformed addressable
records, and unexpected processing exceptions return their SQS `messageId` as a
batch-item failure. A record without an addressable `messageId` fails the
invocation.

The target SQS policy is `maxReceiveCount = 3`. After DLQ transfer, the local
user remains `DELETION_PENDING`.

## PREVIEW Dramatiq retries

PREVIEW uses one initial Dramatiq execution plus two retries. The actor raises a
dedicated retry exception only for `WAITING_FOR_IMPORTS` and
`RETRYABLE_FAILURE`; `COMPLETED` and `NOOP` finish normally.

## Processing executions vs SQS receives

An SQS receive is a transport attempt. A processing execution is one call to
the account-deletion orchestrator. There is no persistent execution counter in
the user model, and duplicate receives may resolve to `NOOP` without repeating
external work.

## Logging and sensitive data

Structured logs may include the Lambda request ID, SQS message ID, internal
user ID, disposition, failed-key count, and exception type. They must not
include email addresses, provider user IDs, authorization tokens, full queue
bodies, or storage-key inventories.

## Production storage boundary

PREVIEW resolves the LOCAL adapter and production resolves the S3 adapter
through the same centralized storage boundary. Account deletion passes
`StorageLocation.USER_MEDIA` explicitly, attempts every unique key, and treats
an already-missing S3 object as success. There is no fallback to Lambda-local
disk.

## Maintenance recovery

Maintenance finds stale `DELETION_PENDING` users without active imports or an
existing pending intent, then atomically schedules and dispatches ID-only
account-deletion work. Maintenance never executes account deletion directly.

## Deferred work

- S3 storage deletion is implemented by P9; client media access belongs to P10.
- Scheduled stale-pending recovery is implemented by P8A maintenance.
- Infrastructure, Lambda packaging, queue/DLQ resources, and alarms are
  separate production phases.
- Optional completion email and provider/local reconciliation remain future
  product and maintenance work.
