# S3 Storage Provider Design

## Scope

P9 adds an S3 implementation behind the centralized storage boundary while
preserving LOCAL behavior. It covers backend and worker storage operations
only. Browser media access remains unavailable for S3 until P10.

## Contracts

`get_storage_service()` selects either the LOCAL or S3 provider. It does not
select a logical storage location. Every `save`, `read`, and `delete` call
passes `StorageLocation.USER_MEDIA` explicitly.

Providers resolve the logical location to a provider-specific locator:

```text
LOCAL -> Path
S3    -> bucket name
```

P9 defines these write purposes and key prefixes:

```text
IMPORT_SOURCE  -> imports/source
IMPORT_DERIVED -> imports/derived
RECIPE_MEDIA   -> recipes/media
TEMPORARY      -> temporary
```

Keys are purpose-first and never start with `users/`. A write context contains
the owner ID, purpose, and owning entity ID so key construction remains inside
the storage module rather than domain call sites.

## Persistence

Each environment uses one dedicated private user-media bucket. Existing
`RecipeImage` and `ImportJobSource` records continue to persist object key,
MIME type, and size metadata. `StoredFile` remains transient. P9 does not add a
`StorageObject` table, checksum, deduplication, persisted bucket, persisted
location, or persisted purpose. Existing records therefore implicitly belong
to `USER_MEDIA`.

## Transaction Boundaries

Storage, provider, image-processing, and other network I/O must not run while a
database transaction is open. Primary import uploads are prepared before the
import-job transaction. Cover source reads, image processing, and cover writes
are prepared before the success-persistence transaction. Database failures and
duplicate or capacity rejection compensate any files prepared by the current
operation.

Recipe deletion, account deletion, and import cleanup remain retryable and
idempotent. Deleting an already absent S3 object is successful. Missing reads
produce a stable storage not-found error; other SDK failures remain storage
operation failures.

## Deferred Work

P9 does not provision buckets, IAM, encryption, lifecycle, versioning, or other
AWS infrastructure. Presigned media access is P10. The storage-backed P8B
maintenance operations remain deferred until after P9. No migration,
multipart upload, checksum, direct browser upload, or frontend change is part
of this iteration.
