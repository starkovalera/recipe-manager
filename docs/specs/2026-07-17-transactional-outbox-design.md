# Transactional Outbox Design

## Scope

This subphase adds one shared transactional outbox for:

- import jobs;
- recipe embeddings;
- account deletion.

SQS, Lambda, EventBridge, S3, Terraform, frontend work, and published-row
retention are excluded.

## Invariant

Whenever committed domain state requires background work, the same database
transaction also creates an ID-only outbox row.

After commit, the application attempts immediate transport publication.
A broker failure leaves the domain state committed and the outbox row pending.

## Message Types

- `IMPORT_JOB` with internal import job ID;
- `RECIPE_EMBEDDING` with internal recipe ID;
- `ACCOUNT_DELETION` with internal user ID.

No domain payload, authentication data, provider identity, media, or exception
message is persisted in the outbox.

## States

- `PENDING`: publication is required or must be retried;
- `PUBLISHED`: transport accepted the message and post-publication persistence
  completed.

The outbox records attempt count, last-attempt timestamp, safe error class name,
publication timestamp, and creation timestamp.

## Delivery Semantics

Delivery is at least once.

A process may successfully send a broker message and terminate before marking
the outbox row published. Reconciliation may then send the same ID again.
Consumers must therefore remain idempotent.

Published rows are retained in this subphase. Retention is a later operational
decision.

## Immediate Dispatch

Normal request and worker flows dispatch the newly committed outbox row
immediately to preserve low latency.

Immediate dispatch failure does not undo committed state:

- an import remains queued;
- an import retry remains queued and retains its notification;
- an embedding remains stale/scheduled;
- an account remains deletion pending.

## Recovery

`python -m app.queueing.reconcile_outbox` dispatches a bounded batch of pending
rows through the configured `QueuePublisher`.

PREVIEW uses Dramatiq. The future SQS adapter will reuse the same outbox and
dispatcher contracts.

## Domain-Specific Publication Success

Embedding publication creates the existing `ENQUEUED` embedding event only
after transport success. The event and the outbox `PUBLISHED` transition are
committed together.

Import and account-deletion publication require no additional persisted domain
event in this subphase.

## Concurrency

Concurrent dispatchers may both send the same pending row. This is acceptable
under at-least-once delivery.

The post-publication state transition locks the outbox row before checking its
status. Only the first successful transition creates embedding's `ENQUEUED`
event and marks the row `PUBLISHED`; subsequent transitions are no-ops.
Dispatching an already published row is also a no-op.
