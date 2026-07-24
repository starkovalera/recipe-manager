# Presigned Media Access Design

## Scope

P10 replaces storage-key-based browser media access with stable domain media
identifiers and provider-specific download grants. S3 grants are short-lived;
LOCAL grants point to an authenticated application endpoint. The phase covers
private user media for both LOCAL and S3 storage while keeping storage keys,
bucket names, and provider-specific locators out of public API responses.

P10 supports two reference types:

```text
recipe_image
import_source_image
```

Upload authorization, direct browser uploads, multipart uploads, CDN delivery,
CloudFront, bucket provisioning, IAM, lifecycle policies, and public sharing are
outside this phase.

## Public Media References

Domain responses expose stable media IDs instead of `mediaUrl` or storage keys.

- `RecipeImageOut` keeps `id` and removes `mediaUrl`.
- `ImportJobSourceOut` exposes its source `id`; image sources use that ID as an
  `import_source_image` reference.
- Storage keys remain persisted internal metadata and are never returned to the
  browser.
- The existing `build_media_url()` helper and key-based media route are removed.
- No database migration is required; both public reference IDs already exist.

A client requests access with an explicit type and ID:

```json
{
  "items": [
    {"type": "recipe_image", "id": "image-id"},
    {"type": "import_source_image", "id": "source-id"}
  ]
}
```

`POST /media/access` accepts between 1 and 100 items. Input order and duplicate
positions are preserved in the response. The service may deduplicate internal
resolution and grant generation work.

## Batch Result Contract

The endpoint uses partial success and returns HTTP `200` for every structurally
valid batch. Each result repeats the requested type and ID and contains exactly
one of `grant` or `error`.

```json
{
  "items": [
    {
      "type": "recipe_image",
      "id": "image-id",
      "grant": {
        "url": "https://example.invalid/signed",
        "expiresAt": "2026-07-24T10:01:00Z",
        "contentType": "image/jpeg",
        "accessMode": "direct"
      }
    },
    {
      "type": "import_source_image",
      "id": "source-id",
      "error": {
        "code": "MEDIA_NOT_FOUND",
        "message": "Media is unavailable."
      }
    }
  ]
}
```

Missing, foreign, lifecycle-ineligible, and otherwise inaccessible media all
produce the same per-item `MEDIA_NOT_FOUND` result. This prevents the endpoint
from disclosing whether another user's media ID exists.

Batch-level failures are limited to conditions that prevent interpreting or
processing the request as a batch:

- `401` for missing or invalid user authentication;
- `422` for malformed items, unsupported reference types, an empty batch, or
  more than 100 items;
- `503` when the configured access provider cannot generate grants.

The service does not convert a provider-wide operational failure into up to 100
repeated item errors.

## Download Grant

A download grant contains:

```text
url
expiresAt
contentType
accessMode
```

`expiresAt` is nullable. The current S3 provider returns an absolute UTC expiry;
the stable authenticated LOCAL endpoint returns `null`. Clients must not persist
expiring direct URLs as durable media identifiers and must request a new grant
after expiry.

`contentType` comes from durable database metadata. P10 does not read the object
body to rediscover its MIME type.

## Download Access Modes

`DownloadAccessMode` describes how the client must retrieve the resource. It is
not a storage-provider enum, an authorization classification, or a public/private
flag.

```text
direct
authenticated_fetch
```

### `direct`

The URL can be assigned directly to a browser resource attribute such as
`<img src>`. The resource is not necessarily public: the URL may contain a
short-lived signature or another bearer capability.

Examples that may use this mode include S3 presigned URLs, CloudFront signed
URLs, CDN URLs, and a future same-origin endpoint whose browser credentials are
sent automatically.

### `authenticated_fetch`

The URL must be requested through the application's authenticated API client.
The frontend converts the response body to a `Blob` and exposes it through an
object URL or another client-managed representation.

The initial LOCAL implementation uses this mode because the current bearer token
cannot be attached by a plain `<img src>` request.

### Why this is not `requiresAuth`

Authorization requirements and browser retrieval mechanics are different
concepts. A cookie-protected same-origin URL can require authorization while
still being usable directly. Conversely, a URL can require custom request
handling even when it does not use application user authentication.

The code and documentation must therefore avoid interpreting `direct` as
"public" or `authenticated_fetch` as "LOCAL". Provider implementations may
change without changing the meaning of either value.

## Domain Authorization And Lifecycle

`MediaAccessService` resolves every public reference to internal storage
metadata only after applying domain ownership and lifecycle rules.

### Recipe images

A `recipe_image` reference is accessible only when:

- the `RecipeImage` exists and is linked to a recipe;
- the recipe belongs to the current user;
- the recipe status is `ACTIVE`.

The status of a related `RecipeResource` does not control media authorization.
`USED`, `IGNORED`, `UNKNOWN`, or `DELETED` are presentation and recipe-editing
states rather than ownership boundaries.

### Import source images

An `import_source_image` reference is accessible only when:

- the `ImportJobSource` exists;
- its type is `IMAGE`;
- `image_storage_key` is present;
- its parent import job belongs to the current user;
- the job status is not `FAILED_ARTIFACTS_REMOVED`.

A terminal `FAILED` job can retain source artifacts for the configured cleanup
period and remains accessible until maintenance removes those artifacts and
moves the job to `FAILED_ARTIFACTS_REMOVED`.

## Application Architecture

`MediaAccessService` is a separate application layer. It owns:

- validating and preserving batch references;
- resolving each `MediaReferenceType` through a strict resolver registry keyed
  by `recipe_image` or `import_source_image`;
- enforcing ownership and lifecycle rules;
- normalizing inaccessible references to `MEDIA_NOT_FOUND`;
- invoking the configured download-grant provider;
- preserving partial-success result ordering.

Domain resolution must not be implemented in API routes or storage adapters.
Routes authenticate, validate schemas, call the service, and serialize results.

Provider-specific URL construction remains behind a download-access provider
boundary selected at runtime. This boundary owns retrieval mechanics only. It
receives already-authorized internal metadata such as `StorageLocation`,
storage key, MIME type, and the original public reference; it does not query
domain ownership.

The media-access boundary is separate from the existing `StorageService`
`save`/`read`/`delete`/`list` contract. Implementations may share provider
configuration or client construction, but download-grant behavior must not add
user authorization semantics to `StorageService`.

## Provider Behavior

### S3

The S3 access provider generates a presigned `GET` URL for
`StorageLocation.USER_MEDIA` with a 60-second lifetime.

It returns:

```text
accessMode = direct
expiresAt = signing time + 60 seconds
```

The service treats durable database metadata as the access-path source of truth.
It does not issue `HeadObject` before signing. A missing physical object can
therefore produce a validly signed URL whose later GET returns `404`; integrity
and orphan-detection maintenance are responsible for detecting storage/database
inconsistency. Avoiding per-object HEAD requests keeps batches bounded to grant
generation rather than up to 100 additional network checks.

### LOCAL

The LOCAL access provider returns an authenticated domain-ID endpoint rather
than a path containing the storage key:

```text
GET /media/{media_type}/{media_id}
```

It returns:

```text
accessMode = authenticated_fetch
expiresAt = null
```

The GET endpoint authenticates the user and resolves the domain reference again
before returning `FileResponse`. The URL itself does not grant access and can be
called directly only by an authorized API client. Re-resolution prevents a
client from converting the stable route into a bearer-free capability.

The temporary provider check based on `isinstance(LocalStorageService)` is
removed. Runtime access-provider selection handles LOCAL and S3 behavior.

## Frontend Behavior

Frontend media state is keyed by the stable pair `(type, id)`, never by an access
URL.

- Batch visible references through `POST /media/access` where practical.
- For `direct`, assign the URL directly to the image or other browser resource.
- For `authenticated_fetch`, request the URL through the authenticated API
  client, convert the response to a `Blob`, create an object URL, and revoke it
  when replaced or unmounted.
- Do not treat `accessMode` as a provider identifier.
- Do not reuse a direct URL after `expiresAt`; request a replacement grant.
- Render successful items even when other batch entries return
  `MEDIA_NOT_FOUND`.

The existing URL-shape checks such as `isApiMediaUrl()` are removed. Retrieval
behavior is selected only from `accessMode`.

## Security And Observability

- Public API responses and frontend types contain no storage keys, bucket names,
  local paths, or provider locators.
- Missing and foreign IDs are deliberately indistinguishable.
- Presigned URLs and their query signatures must not be written to application
  logs, error details, analytics payloads, or durable database fields.
- Access logs may record reference type, media ID, result code, access mode, and
  batch counts.
- The LOCAL GET endpoint repeats authorization even after a successful batch
  resolution.
- Only `USER_MEDIA` is eligible. `SYSTEM_ARTIFACTS` is never exposed through
  this API.

## Documentation And Code Comments

P10 adds `docs/media-access.md` as the durable operational contract. It must
cover the domain-ID flow, batch semantics, access-mode meaning, provider
behavior, expiry, frontend responsibilities, security rules, and the boundary
between download and upload contracts.

Code comments are required in these locations:

- every `DownloadAccessMode` enum value, explaining browser behavior and
  explicitly warning that the value does not imply provider or public/private
  status;
- `DownloadGrant`, stating that `access_mode` describes client retrieval
  mechanics;
- the frontend branch that handles `authenticated_fetch`, explaining why a
  bearer token cannot be added to a plain `<img src>` request.

Contract tests must enforce these meanings so future implementations do not turn
`DownloadAccessMode` into an implicit `LOCAL`/`S3` enum.

## Testing

Backend coverage includes:

- request validation and the 100-item limit;
- input-order and duplicate preservation;
- mixed grant and `MEDIA_NOT_FOUND` results;
- indistinguishable missing and foreign references;
- recipe ownership, active status, and resource-status independence;
- import ownership, image type, required storage key, retained failed artifacts,
  and `FAILED_ARTIFACTS_REMOVED` denial;
- LOCAL authenticated endpoint authorization and file responses;
- S3 presign parameters, 60-second expiry, and no `HeadObject` call;
- provider-wide failures returning `503`;
- absence of storage keys and legacy `mediaUrl` in public schemas.

Frontend coverage includes:

- batching references and matching ordered results;
- direct URLs assigned without authenticated blob fetching;
- authenticated fetch using the API client and object-URL cleanup;
- partial failures not suppressing successful images;
- grant refresh after direct URL expiry;
- no retrieval decisions based on URL shape.

Gateway tests cover both `POST /media/access` and the authenticated LOCAL GET
route. Existing key-based media routes are removed from gateway configuration.

## Download And Upload Boundary

`DownloadGrant` is not reused for uploads. A later upload phase defines a
separate `UploadIntent` that may need method, headers, form fields, size limits,
content restrictions, multipart state, and expiry. `DownloadAccessMode` remains
specific to consuming a downloadable browser resource and does not constrain
future user-image upload designs.

## Deferred Work

P10 does not add a generic `Media` or `StorageObject` table, persist grants,
perform physical-object existence checks, provision AWS resources, configure
bucket CORS, implement direct browser uploads, add public sharing, or introduce
CDN/CloudFront delivery. Those changes require separate designs when their
product requirements are known.
