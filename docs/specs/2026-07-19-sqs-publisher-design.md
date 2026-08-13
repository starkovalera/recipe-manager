# SQS Publisher Design

## Scope

This subphase adds the production SQS transport behind the existing
`QueuePublisher` and transactional outbox.

It does not provision AWS resources and does not add Lambda consumers,
EventBridge, IAM, DLQ configuration, S3, Terraform, or frontend changes.

## Runtime selection

- PREVIEW uses `DramatiqQueuePublisher` and Redis.
- Configurations with `QUEUE_PROVIDER=SQS` use `SqsQueuePublisher`.

Domain scheduling and the transactional outbox are transport independent.

## Queues

The publisher targets three separate standard queues:

- imports;
- embeddings;
- account deletion.

Maintenance publishing remains deferred to the maintenance dispatcher
subphase.

## Wire contracts

Each queue has one strict ID-only JSON contract:

- imports: `{"importJobId":"<internal-id>"}`;
- embeddings: `{"recipeId":"<internal-id>"}`;
- account deletion: `{"userId":"<internal-id>"}`.

The payload does not include a message type because queue selection defines
the operation. It does not contain outbox IDs, domain payloads, source data,
media, email, provider identities, authentication data, or credentials.

## Configuration

Selecting SQS requires:

- AWS region;
- imports queue URL;
- embeddings queue URL;
- account-deletion queue URL.

The URLs must be non-empty and distinct.

AWS credentials are not application settings. boto3 uses the standard AWS
credential provider chain. Production will later provide credentials through
an IAM role or instance profile.

## Client lifecycle

The boto3 SQS client is created lazily on the first publication. Importing the
application and constructing the queue publisher must not perform credential
resolution or network access.

## Publication behavior

Each publisher method validates the ID through its typed message model,
serializes the camelCase JSON body, calls `SendMessage` with the configured
queue URL, and requires a non-empty `MessageId` response.

AWS SDK errors propagate to the transactional outbox. The adapter does not
implement an additional retry loop.

## Delivery semantics

Delivery remains at least once. The transactional outbox, not the SQS adapter,
records attempts and retries pending work.

The SQS adapter does not alter outbox state, embedding events, or domain state.
