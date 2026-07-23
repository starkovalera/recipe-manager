# Import Error Handling and Retry Policy

## Terminology

`ImportJob.error_code` is the high-level persisted failure category. Its values
are `IMPORT_FAILED`, `IMPORT_PROCESSING_FAILED`, and
`IMPORT_EXTRACTION_FAILED`.

`ImportJob.error_message` is the current schema field containing the stable
detailed code for terminal failures. Despite the field name, it does not store
an arbitrary provider or exception message.

The `IMPORT_FAILED` event payload contains the detailed code, high-level code,
stable message, retry classification, terminal decision, attempt count, maximum
attempts, and safe domain details. Raw exception messages are not persisted for
`UNEXPECTED_ERROR`.

## Stable error policy

`IMPORT_ERROR_POLICIES` is the single code-level source of truth for automatic
and manual retry classification. Every stable detailed import error must have an
explicit entry.

<!-- IMPORT_ERROR_POLICY_TABLE:START -->
| Detailed code | High-level code | Stage | Automatic SQS retry | Manual retry |
|---|---|---|---:|---:|
| `UNEXPECTED_ERROR` | `IMPORT_FAILED` | `INTERNAL` | Yes | Yes, while attempts remain |
| `SECONDARY_RESOURCE_UPLOADING_FAILED` | `IMPORT_PROCESSING_FAILED` | `PROCESSING` | Yes | Yes, while attempts remain |
| `STALE_IMPORT_RECOVERY` | `IMPORT_PROCESSING_FAILED` | `PROCESSING` | Yes | Yes, while attempts remain |
| `RESULT_PARSE_FAILED` | `IMPORT_EXTRACTION_FAILED` | `EXTRACTION` | Yes | Yes, while attempts remain |
| `INVALID_EXTRACTION_RESULT` | `IMPORT_EXTRACTION_FAILED` | `EXTRACTION` | Yes | Yes, while attempts remain |
| `EXTRACTOR_UNAVAILABLE` | `IMPORT_EXTRACTION_FAILED` | `EXTRACTION` | Yes | Yes, while attempts remain |
| `NOT_A_RECIPE` | `IMPORT_EXTRACTION_FAILED` | `EXTRACTION` | No | Yes, while attempts remain |
| `RECIPE_TOO_LONG` | `IMPORT_EXTRACTION_FAILED` | `EXTRACTION` | No | Yes, while attempts remain |
<!-- IMPORT_ERROR_POLICY_TABLE:END -->

Low-confidence extraction is classified as `NOT_A_RECIPE`.

## Attempt limits

`MAX_IMPORT_ATTEMPTS=3` means three total started processing attempts:

```text
delivery/claim 1 -> attempt_count=1
retry delivery/claim 2 -> attempt_count=2
retry delivery/claim 3 -> attempt_count=3
no fourth processing claim
```

`attempt_count` increments only during an atomic `QUEUED -> RUNNING` claim.
SQS `ApproximateReceiveCount` is independent and is not the domain attempt
counter.

Automatic retry is policy-controlled and reuses the same SQS record. Manual
retry creates a new durable outbox message. All current terminal detailed codes
remain manually retryable while attempts remain, including `NOT_A_RECIPE` and
`RECIPE_TOO_LONG`. A manual retry of a deterministic code may fail for the same
reason again. Changing manual retry eligibility is outside P5.

## ImportJob state machine

| Situation | Before | During | After | Lambda |
|---|---|---|---|---|
| success | `QUEUED` | `RUNNING` | `SUCCEEDED` / `SUCCEEDED_WITH_FLAGS` | acknowledge |
| duplicate/missing/non-queued | current state | no claim | unchanged | acknowledge |
| retryable, attempts remain | `QUEUED` | `RUNNING` | `QUEUED` | partial failure |
| retryable, no attempts remain | `QUEUED` | `RUNNING` | `FAILED` | acknowledge |
| non-retryable | `QUEUED` | `RUNNING` | `FAILED` | acknowledge |
| malformed SQS message | unchanged | no claim | unchanged | partial failure / DLQ later |

The intermediate retry state is exact:

```text
status = QUEUED
attempt_count = preserved
started_at = NULL
finished_at = NULL
error_code = NULL
error_message = NULL
created_recipe_id = NULL
```

Missing, terminal, `RUNNING`, and otherwise non-`QUEUED` jobs are not claimed
and return `NOOP`.

## Events and notifications

An intermediate retryable failure records:

```text
IMPORT_FAILED event: yes, terminal=false
failure notification: no
```

A terminal failure records:

```text
IMPORT_FAILED event: yes, terminal=true
failure notification: yes
```

Manual retry retains its existing user-visible import-started notification and
is independent of automatic retry classification.

## Artifact cleanup

Intermediate retryable failure cleanup is:

```text
secondary/current-attempt cleanup: yes
primary cleanup: no
```

Terminal failure cleanup is:

```text
secondary/current-attempt cleanup: yes
primary cleanup: yes when cleanup is enabled
```

## Processing dispositions

The import service returns one explicit disposition:

- `SUCCEEDED`: processing completed and the recipe was persisted;
- `NOOP`: the job was missing or could not be claimed from `QUEUED`;
- `PERMANENT_FAILURE`: processing failed terminally and the message is
  acknowledged;
- `RETRYABLE_FAILURE`: the job returned to `QUEUED` and the message must be
  retried.

Business error classification belongs to the import domain. Infrastructure
adapters consume the resulting disposition without duplicating error policies.

## Lambda partial-batch behavior

The Import Lambda validates each existing `ImportJobQueueMessage` and returns
AWS `batchItemFailures`. `SUCCEEDED`, `NOOP`, and `PERMANENT_FAILURE`
acknowledge the current SQS record. `RETRYABLE_FAILURE` adds that record's SQS
`messageId` to `batchItemFailures`.

Malformed JSON, invalid message schema, or an unexpected processing exception
fails only an addressable record. A missing or blank SQS `messageId` fails the
entire invocation because no valid partial-batch identifier exists.

## Message/infrastructure failures

| Failure | Domain code/state | Lambda behavior |
|---|---|---|
| malformed JSON with message ID | no change | partial batch failure |
| schema-invalid body | no change | partial batch failure |
| missing/non-string body | no change | partial batch failure |
| missing/blank message ID | no change | fail entire invocation |
| DB failure before claim | no attempt increment | partial batch failure through raised exception |
| unexpected service exception escaping processing | depends on last committed state | partial batch failure |
| missing job | no change | `NOOP`, acknowledge |
| job `RUNNING` or terminal | no change | `NOOP`, acknowledge |

Malformed or infrastructure-failing messages may reach the future DLQ after
infrastructure redrive limits are exhausted. P5 does not provision those limits
or the DLQ.

## Duplicate delivery and stale RUNNING jobs

Duplicate delivery is idempotent at the claim boundary. Only `QUEUED` jobs are
claimed, so a concurrent duplicate for a `RUNNING` job and a delivery for a
terminal job both return `NOOP` without running the pipeline again.

P5 does not reclaim stale `RUNNING` jobs. Detection and recovery remain owned by
P8 maintenance.

Old terminal failed jobs may retain artifacts when immediate best-effort cleanup
was incomplete. P8B1 maintenance deletes only keys proven safe for that job and
moves a fully cleaned job to `FAILED_ARTIFACTS_REMOVED`. This status is terminal
and cannot be manually or automatically retried. Cleanup anomalies leave the job
as `FAILED` and produce a private maintenance report.

## Adding a new error code

1. Define the stable detailed code and its domain exception behavior.
2. Add exactly one corresponding policy to `IMPORT_ERROR_POLICIES`.
3. Regenerate the table between the policy markers in this document using
   `render_import_error_policy_table()`.
4. Update focused tests for classification and lifecycle behavior.

CI rejects declared codes without a policy and rejects a policy table that does
not exactly match the registry renderer.
