# Embedding Lambda Adapter Design

## Scope

P6 adds an SQS-triggered embedding Lambda adapter around the existing embedding
service. It also makes embedding claims duplicate-safe and gives the service an
explicit processing result.

Lambda packaging, AWS resources, IAM, S3, stale-running maintenance recovery,
OpenAI exception taxonomy, account deletion, and maintenance are excluded.

## Processing dispositions

- `SUCCEEDED`: the vector was saved and the embedding is `READY`;
- `NOOP`: the recipe is missing, blocked by open review flags, or already ready
  for the current input and model;
- `REQUEUED`: the recipe changed during the provider call and a new durable
  embedding outbox message was created;
- `BUSY`: the embedding is already `RUNNING`; no second provider call starts;
- `RETRYABLE_FAILURE`: the provider failed and the embedding was saved as
  `FAILED`.

## Claiming

A short transaction locks the active recipe row. The lock is the per-recipe
claim boundary. The transaction decides the disposition or changes a claimable
embedding to `RUNNING` and writes `STARTED`. The provider call runs only after
that transaction commits.

## Retry semantics

The Lambda returns `BUSY` and `RETRYABLE_FAILURE` records through
`batchItemFailures`. `SUCCEEDED`, `NOOP`, and `REQUEUED` are acknowledged.

PREVIEW uses Dramatiq with two retries after the initial execution, for at most
three processing executions. Production retry count is owned by the future SQS
redrive policy, initially `maxReceiveCount = 3`.

`failed_attempts` counts provider failures only. It is not an SQS receive count
and is not reset by manual retry.

## Crash recovery

A crash after the `RUNNING` claim may leave the embedding running. Duplicate
messages return `BUSY`; P8 maintenance will recover stale running rows.
