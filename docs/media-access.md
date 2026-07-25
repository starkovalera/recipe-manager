# Media Access

P10 exposes private user media through stable domain references and temporary
download grants. Browser clients never receive storage keys, bucket names,
filesystem paths, or provider locators.

## Stable references

The supported reference types are:

- `recipe_image`, backed by `RecipeImage.id`;
- `import_source_image`, backed by `ImportJobSource.id`.

Recipe responses expose image IDs. Import-job sources expose their own IDs.
Access URLs are retrieval details and must not be stored as durable media
identifiers.

## Batch access

Authenticated clients request 1-100 references:

```http
POST /media/access
Content-Type: application/json

{"items":[{"type":"recipe_image","id":"image-id"}]}
```

Input order and duplicate positions are preserved. A valid batch returns `200`
with one result per input. Each result contains exactly one `grant` or `error`.
Missing, foreign, detached, lifecycle-ineligible, and unusable references all
return the same per-item error:

```json
{"code":"MEDIA_NOT_FOUND","message":"Media is unavailable."}
```

This deliberately prevents existence disclosure. Malformed batches return
`422`, missing authentication returns `401`, and provider-wide grant failure
returns `503 MEDIA_ACCESS_NOT_AVAILABLE` rather than repeated item errors.

## Download grants

A grant contains `url`, nullable UTC `expiresAt`, durable `contentType`, and
`accessMode`. `accessMode` describes browser retrieval mechanics. It is not a
provider name or a public/private classification.

- `direct`: assign the URL directly to `<img src>` or a similar attribute.
- `authenticated_fetch`: fetch through the authenticated API client, convert
  the response to a Blob, and use a revocable object URL. The current bearer
  token cannot be attached by a plain `<img src>` request.

`DownloadGrant` is not an upload contract. A future `UploadIntent` may require
method, headers, form fields, content constraints, multipart state, and expiry.

## Authorization and lifecycle

`recipe_image` requires a linked `ACTIVE` recipe owned by the current user.
Related `RecipeResource` presentation status does not affect authorization.

`import_source_image` requires an IMAGE source with a storage key on an import
owned by the current user. `FAILED` remains accessible while artifacts are
retained; `FAILED_ARTIFACTS_REMOVED` is inaccessible.

The LOCAL `GET /media/{media_type}/{media_id}` endpoint authenticates and
resolves the reference again. It never accepts a storage key from the client.

## Providers

LOCAL returns an `authenticated_fetch` grant with a stable API path and no
expiry. The GET endpoint validates local path containment and returns the file
bytes and stored content type.

S3 returns a `direct` presigned `get_object` URL for the configured private
`USER_MEDIA` bucket. The TTL is 60 seconds. Signing uses the existing lazy boto3
client and standard credential chain. No `HeadObject` request is made: durable
database metadata is the access-path source of truth, while integrity
maintenance reports physical drift.

## Frontend responsibilities

Frontend state and query keys use `(type, id)`. Visible references are batched.
Successful siblings render when another item is unavailable. Direct grants are
refreshed before expiry. Authenticated Blob object URLs are revoked on
replacement and unmount. Default SVG assets remain local and require no grant.

## Security and logging

Only `StorageLocation.USER_MEDIA` is eligible. `SYSTEM_ARTIFACTS` is never
exposed. Presigned URLs and signatures must not be logged, persisted, included
in analytics, or copied into error details. Safe diagnostics may include media
type, media ID, result code, access mode, and aggregate batch counts.

P10 does not add upload grants, public sharing, CDN delivery, persistent grants,
S3 proxying, per-grant physical-object checks, or AWS provisioning.
