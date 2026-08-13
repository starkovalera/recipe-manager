# Account-deletion Lambda Adapter Design

## Scope

P7 adds the account-deletion SQS Lambda entrypoint and explicit processing
outcomes. It does not provision AWS resources, package Lambda images, implement
S3, or add maintenance scheduling.

## Durable lifecycle

The persisted user lifecycle remains:

`ACTIVE -> DELETION_PENDING -> physically deleted`.

Processing failures never return the user to `ACTIVE` and do not introduce a
terminal failed user status. A user remains `DELETION_PENDING` until deletion
completes or operational recovery republishes the work.

## Processing dispositions

- `COMPLETED`: provider identity, storage objects, and local user deletion
  completed.
- `NOOP`: the user is missing or no longer `DELETION_PENDING`.
- `WAITING_FOR_IMPORTS`: at least one owned import is `QUEUED` or `RUNNING`.
- `RETRYABLE_FAILURE`: a provider, storage, configuration, or final database
  operation did not complete.

`COMPLETED` and `NOOP` acknowledge the queue record. `WAITING_FOR_IMPORTS` and
`RETRYABLE_FAILURE` request transport retry.

## Operation order

1. Load the pending user and unique storage inventory.
2. Stop before external operations when active imports exist.
3. Delete the external authentication identity idempotently.
4. Attempt deletion of every unique storage key.
5. Re-read and lock the pending user.
6. Delete and commit the local user.
7. Report `COMPLETED` only after the final commit.

## Duplicate delivery

No `DELETION_RUNNING` lease is added. Duplicate safety relies on idempotent
provider deletion, idempotent storage deletion, unique storage inventory, and a
final locked pending-user check. A later delivery after successful deletion is
`NOOP`.

## Retry boundaries

Production SQS will use `maxReceiveCount = 3`. The application does not read or
persist SQS receive count. PREVIEW uses initial Dramatiq execution plus two
retries, for three total executions.

After SQS redrive to the dedicated DLQ, the user remains
`DELETION_PENDING`. P8 maintenance will republish stale pending users through a
new durable outbox intent.

## Storage boundary

PREVIEW uses `LocalStorageService`. `STORAGE_PROVIDER=S3` fails explicitly in
P7 because P9 owns the S3 implementation. Production account-deletion Lambda is
not deployable until P9 connects the storage seam to S3. The code must never
fall back to Lambda-local filesystem storage.

## Logging and data

Lambda record logs contain request/message IDs, internal user ID, disposition,
error type, and failed-key count only. They do not contain queue bodies, email,
provider IDs, tokens, secrets, provider responses, or storage inventories.
