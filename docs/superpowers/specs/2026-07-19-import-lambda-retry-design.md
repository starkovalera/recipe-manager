# Import Lambda Retry Design

## Scope

P5 adds the import SQS Lambda entrypoint, explicit processing outcomes, and an
exhaustive import error policy.

Lambda packaging, AWS infrastructure, IAM, S3, video-duration validation, and
other Lambda entrypoints are excluded.

## Processing outcomes

- `SUCCEEDED`: import completed successfully;
- `NOOP`: the job is missing or not queued;
- `PERMANENT_FAILURE`: the current SQS record is acknowledged;
- `RETRYABLE_FAILURE`: the SQS record is returned in `batchItemFailures`.

## Attempts

`MAX_IMPORT_ATTEMPTS=3` means three total processing attempts.

`attempt_count` increments only when the job is atomically claimed from
`QUEUED` to `RUNNING`. SQS receive count is independent.

## Intermediate retry state

A retryable failure with attempts remaining changes the job to `QUEUED` while
preserving `attempt_count` and clearing current result, error, and attempt
timestamps.

It writes a non-terminal `IMPORT_FAILED` diagnostic event, creates no final
failure notification, deletes current-attempt secondary artifacts, and retains
primary uploads.

## Terminal state

A non-retryable failure, or a retryable failure after the final allowed attempt,
changes the job to `FAILED`.

It writes a terminal `IMPORT_FAILED` event, creates a failure notification, and
cleans primary uploads when cleanup is enabled.

## Manual retry

Manual retry remains available for every `FAILED` job while attempts remain,
including `NOT_A_RECIPE` and `RECIPE_TOO_LONG`.

## Error policies

Automatic retry:

- `UNEXPECTED_ERROR`;
- `SECONDARY_RESOURCE_UPLOADING_FAILED`;
- `RESULT_PARSE_FAILED`;
- `INVALID_EXTRACTION_RESULT`;
- `EXTRACTOR_UNAVAILABLE`.

No automatic retry:

- `NOT_A_RECIPE`;
- `RECIPE_TOO_LONG`.

Low-confidence extraction uses `NOT_A_RECIPE`.

## Lambda event handling

The handler validates existing `ImportJobQueueMessage` bodies and returns AWS
partial batch failures.

`SUCCEEDED`, `NOOP`, and `PERMANENT_FAILURE` acknowledge the record.
`RETRYABLE_FAILURE`, malformed JSON, schema failures, and unexpected service
exceptions fail only the identified record.

A missing or blank SQS `messageId` fails the entire invocation.

## Duplicate delivery

Missing and non-queued jobs are `NOOP`. A duplicate delivery must not process a
`RUNNING` or terminal job. Stale `RUNNING` recovery remains P8 maintenance work.

## Documentation invariant

`docs/import-error-handling.md` contains a generated policy table that must
match the single `IMPORT_ERROR_POLICIES` registry. Tests reject undeclared,
undocumented, or mismatched codes.
