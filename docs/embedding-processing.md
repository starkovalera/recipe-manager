# Embedding Processing

## Purpose and source of truth

`RecipeEmbedding` stores the current indexing state for one recipe. Its event
history is diagnostic only and never reconstructs current state. The embedding
processing service owns domain decisions; Lambda and Dramatiq only map its
explicit result to their transport retry behavior.

## Statuses

- `STALE`: work is scheduled or the recipe changed while work was running.
- `RUNNING`: one worker has durably claimed the active recipe.
- `READY`: the current model and input hash have a saved vector.
- `FAILED`: the provider call failed and failure details were persisted.
- `SKIPPED_DUE_TO_FLAGS`: open review flags currently block embedding.

## Dispositions

- `SUCCEEDED`: the vector was saved and status is `READY`.
- `NOOP`: the active recipe is missing, has open flags, or is already current.
- `REQUEUED`: input changed during the provider call and a new durable outbox
  message was created.
- `BUSY`: another delivery already has the embedding in `RUNNING`.
- `RETRYABLE_FAILURE`: the provider failed and status is durably `FAILED`.

## Atomic claim table

| State at claim | Mutation | Event | Result |
| --- | --- | --- | --- |
| recipe missing or not `ACTIVE` | none | none | `NOOP` |
| open review flags | `SKIPPED_DUE_TO_FLAGS` | `SKIPPED_DUE_TO_FLAGS` | `NOOP` |
| current `READY` model and hash | none | `ALREADY_READY` | `NOOP` |
| `RUNNING` | none | none | `BUSY` |
| `FAILED`, `STALE`, or outdated `READY` | set `RUNNING`, model, hash, and attempt time | `STARTED` | provider context |

The claim transaction locks the active `Recipe` row with `FOR UPDATE`. That row
is the per-recipe claim boundary; no Redis or distributed lock is used.

## Provider call transaction boundary

The claim transaction commits before calling the provider. No application DB
session or row lock remains open while the provider computes the vector. Saving
success or failure happens in a new short database transaction.

## Success lifecycle and event order

For unchanged input, the event order is:

```text
STARTED -> PROVIDER_SUCCEEDED -> SAVED
```

The vector is stored, status becomes `READY`, and processing returns
`SUCCEEDED`.

## Provider failure lifecycle

A provider exception is persisted as `FAILED`, increments `failed_attempts`,
sets `last_error_at`, and writes `FAILED`. The service returns
`RETRYABLE_FAILURE` instead of re-raising the provider exception. If persisting
that failure fails, the persistence exception propagates to the transport.

No user notification is created for embedding failure. Embedding state, events,
internal UI, and logs provide diagnostics without adding product notification
noise.

## `failed_attempts` semantics

`failed_attempts` counts failed provider calls. It is not an SQS receive count,
not a Dramatiq delivery count, and not an application retry limit. A successful
claim after `FAILED` preserves the count. Manual retry does not reset it.

## Recipe-change requeue lifecycle

If the recipe input hash changes during provider execution, completion stores
`STALE`, writes `PROVIDER_SUCCEEDED` and `STALE_REQUEUED`, and atomically creates
a new pending `RECIPE_EMBEDDING` outbox message. Post-commit dispatch is attempted
and the current processing result is `REQUEUED` even when immediate dispatch
fails, because the durable outbox row remains available for reconciliation.

## Lambda partial-batch mapping

| Disposition | SQS result |
| --- | --- |
| `SUCCEEDED` | acknowledge |
| `NOOP` | acknowledge |
| `REQUEUED` | acknowledge |
| `BUSY` | include `messageId` in `batchItemFailures` |
| `RETRYABLE_FAILURE` | include `messageId` in `batchItemFailures` |

Malformed addressable records are partial failures. A missing or invalid
`messageId` makes the invocation fail because the record cannot be addressed in
the partial-batch response.

## PREVIEW retry count

PREVIEW uses Dramatiq. Initial processing execution plus two retries means at
most three executions. `EMBEDDING_TASK_MAX_RETRIES` defaults to `2`; Dramatiq
retries only `BUSY` and `RETRYABLE_FAILURE`. `REQUEUED` is acknowledged because
replacement work already has its own outbox message.

## PROD SQS receive and DLQ boundary

Production retry delivery is owned by SQS. `maxReceiveCount=3` is the target
redrive setting and will be configured by Terraform in a later iteration. P6
does not add queues, DLQs, IAM, packaging, or other AWS infrastructure.

## Manual retry behavior

The existing internal retry endpoint schedules fresh durable outbox work and
does not reset `failed_attempts`.

## Duplicate delivery behavior

A duplicate arriving after work is current returns `NOOP`. A duplicate arriving
while another execution owns `RUNNING` returns `BUSY` without adding `STARTED`,
mutating the embedding, or calling the provider.

## Crash while `RUNNING` and P8 recovery

A crash after the claim commit can leave an embedding in `RUNNING`. Duplicates
remain `BUSY`; maintenance detects stale `RUNNING` rows, changes them to
`STALE`, records `STALE_REQUEUED`, and creates a durable outbox intent without
calling the embedding provider.

## Logging and sensitive-data rules

Lambda logs may include AWS request ID, SQS message ID, validated recipe ID,
disposition, and exception type. They must not contain full SQS events, message
bodies, embedding input text, or vectors.
