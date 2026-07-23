# S3 User-Media Storage

P9 adds a provider-neutral storage boundary for private user media. Runtime
code selects one `StorageProvider`, then each operation names its logical
`StorageLocation` explicitly.

## Vocabulary

- `StorageProvider` selects the `LOCAL` or `S3` implementation.
- `StorageLocation` selects a logical root or bucket for an operation:
  `USER_MEDIA` or private `SYSTEM_ARTIFACTS`.
- `StorageLocator` is provider-specific: a local `Path` or an S3 bucket name.
- `StorageUserPurpose` selects a user-media key prefix.
- `StorageSystemPurpose` selects a private operational-artifact key prefix.
- `StorageSaveContext` is the protocol implemented by immutable
  `StorageUserContext` and `StorageSystemContext` key builders.

`get_storage_service()` selects only the provider. The centralized runtime
mapping resolves `USER_MEDIA` to `UPLOAD_DIR`/`S3_USER_MEDIA_BUCKET_NAME` and
`SYSTEM_ARTIFACTS` to `SYSTEM_ARTIFACTS_DIR`/
`S3_SYSTEM_ARTIFACTS_BUCKET_NAME`.

## Object keys

P9 uses purpose-first keys and never adds a `users/` prefix:

```text
imports/source/{owner}/{job}/{uuid}.{ext}
imports/derived/{owner}/{job}/{uuid}.{ext}
recipes/media/{owner}/{recipe}/{uuid}.{ext}
maintenance/reports/{report-type}/{yyyy}/{mm}/{dd}/{timestamp}-{report-id}.json
```

The extension is derived only from an allowlisted original-name suffix. The
original filename is not embedded in the key. Owner and entity identifiers are
validated before key construction.

## Persistence

`StoredFile` is a transient adapter result. Existing `ImportJobSource` and
`RecipeImage` rows remain the durable media metadata. The database stores the
object key, MIME type, size, and existing domain fields. Current rows imply
`StorageLocation.USER_MEDIA`, so location is not persisted.

P9 does not add a `StorageObject` table, checksums, deduplication, multipart
uploads, or direct browser uploads.

## Transactions and compensation

Storage and provider I/O runs outside database transactions:

- import requests validate and preflight, allocate a job ID, upload primary
  files, then repeat dedupe and active-limit checks in the authoritative
  persistence transaction;
- partial uploads, a final limit failure, a duplicate race, or persistence
  failure delete only objects created by that request;
- URL images and video posters use `IMPORT_DERIVED` and are tracked as
  current-attempt secondary files;
- cover guard, source read, rendering, and cover save complete before the
  import-success transaction; that transaction only attaches prepared ORM
  objects;
- retryable import failures delete current-attempt derived files and preserve
  primary uploads; terminal failures also clean primary uploads;
- recipe and account deletion snapshot keys, close the database scope, attempt
  every object deletion, then perform the final locked database deletion;
- a storage failure leaves recipe or account state pending for maintenance
  retry. Missing S3 objects are an idempotent delete success.

Cleanup failures are logged and do not replace the original import-creation or
processing error.

## Provider behavior

LOCAL supports nested purpose-first keys and legacy flat keys. S3 uses a lazy
boto3 client and exact `put_object`, `get_object`, and `delete_object` calls.
Missing reads map to `StorageObjectNotFoundError`; delete remains idempotent.
Both adapters implement bounded `list_objects`: LOCAL uses a sorted key cursor,
while S3 uses its opaque continuation token.
AWS credentials use the standard boto3 credential chain and are not application
settings.

LOCAL media URLs preserve that distinction at the API and gateway boundary.
Canonical nested keys use
`/media/{namespace}/{kind}/{owner_id}/{entity_id}/{object_name}`; legacy flat
keys use `/legacy-media/{storage_key}`. This fixed-depth split is required by
the local KrakenD CE router and keeps both key formats reachable without
ambiguous routes.

## P9 and P10 boundary

Backend services and workers can save, read, and delete private S3 objects after
P9. Browser/client media access is intentionally unavailable for S3 until P10.
The media endpoint returns `503 MEDIA_ACCESS_NOT_AVAILABLE` without reading S3,
building a public URL, or generating a presigned URL. LOCAL keeps its existing
`FileResponse` behavior.

Bucket creation, policies, encryption, lifecycle rules, versioning, and IAM are
deferred to Terraform infrastructure work. P8B1 adds failed-import cleanup,
read-only orphan detection, and private maintenance reports; destructive orphan
cleanup remains deferred.
