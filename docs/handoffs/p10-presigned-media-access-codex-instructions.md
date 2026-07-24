# P10 — Presigned Media Access: Instructions for Codex

You are implementing P10 in `starkovalera/recipe-manager`.

Work from the current repository state. You already have access to the project and are expected to inspect the actual code before editing. Treat the approved design as authoritative:

- `docs/superpowers/specs/2026-07-24-presigned-media-access-design.md`
- `docs/s3-storage.md`
- `docs/maintenance-processing.md`
- `docs/architecture/production-roadmap.md`

Do not reopen settled architecture decisions unless the current code makes one literally impossible. If that happens, stop and report the conflict before substituting a different design.

## Goal

Replace storage-key-based browser media access with stable domain media references and provider-specific download grants for both LOCAL and S3 storage.

The completed flow must be:

```text
domain API response
    -> stable media reference (type + id)
    -> POST /media/access
    -> per-item DownloadGrant or MEDIA_NOT_FOUND
    -> frontend retrieves the resource according to accessMode
```

## Approved scope

Implement:

- `recipe_image` references backed by `RecipeImage.id`;
- `import_source_image` references backed by `ImportJobSource.id`;
- batch `POST /media/access`, 1–100 items;
- partial-success results;
- S3 presigned GET URLs with a 60-second TTL;
- authenticated LOCAL media retrieval by domain media type and ID;
- frontend support for `direct` and `authenticated_fetch`;
- removal of public `mediaUrl` fields, storage-key URLs, URL-shape routing logic, and the legacy key-based media endpoint;
- gateway changes;
- complete backend/frontend/gateway tests;
- durable documentation in `docs/media-access.md`;
- required explanatory code comments.

Do not implement:

- upload grants or direct browser uploads;
- `UploadIntent`;
- a generic `Media` or `StorageObject` table;
- physical S3 existence checks with `HeadObject`;
- CDN or CloudFront;
- public sharing;
- bucket/IAM/Terraform changes;
- multipart uploads;
- persistent grants;
- unrelated UI redesign or refactoring.

No database migration is expected: the required stable IDs already exist.

## Non-negotiable decisions

### Public references

Public domain responses must expose only stable domain IDs.

- `RecipeImageOut` exposes `id` and no `mediaUrl`.
- `ImportJobSourceOut` exposes its own `id`.
- Public schemas must not expose `storage_key`, bucket names, local paths, or provider locators.
- Delete `build_media_url()` and remove its uses.
- Remove the fixed-depth storage-key route currently shaped like:

```text
GET /media/{namespace}/{kind}/{owner_id}/{entity_id}/{object_name}
```

The replacement LOCAL route is domain-based:

```text
GET /media/{media_type}/{media_id}
```

It must never accept a storage key from the client.

### Batch request

Use an explicit discriminated reference:

```json
{
  "items": [
    {"type": "recipe_image", "id": "image-id"},
    {"type": "import_source_image", "id": "source-id"}
  ]
}
```

Rules:

- minimum 1 item;
- maximum 100 items;
- reject unknown types and extra fields;
- preserve input order;
- preserve duplicate positions;
- internal resolution may deduplicate repeated references.

### Batch response

A structurally valid request returns HTTP `200`, even when some items are inaccessible.

Each result repeats `type` and `id` and contains exactly one of `grant` or `error`.

Example:

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

Use the same per-item `MEDIA_NOT_FOUND` result for:

- missing IDs;
- foreign IDs;
- lifecycle-ineligible records;
- records without usable storage metadata.

Do not disclose whether a foreign record exists.

Batch-level responses:

- `401`: missing or invalid authentication;
- `422`: malformed request, unsupported type, empty batch, or more than 100 items;
- `503`: the configured access provider cannot generate grants.

A provider-wide failure is a batch-level `503`; do not repeat the same provider error inside every item.

### Access modes

Define:

```text
direct
authenticated_fetch
```

`accessMode` describes client retrieval mechanics only.

It is not:

- a LOCAL/S3 enum;
- an authentication-required flag;
- a public/private classification;
- a storage-provider identifier.

Required semantics:

- `direct`: the URL can be assigned directly to `<img src>` or another browser resource attribute.
- `authenticated_fetch`: the URL must be fetched through the authenticated application API client; the body is converted to a `Blob` and exposed through an object URL.

Add comments directly on every enum value. The comments must explain browser behavior and explicitly warn that the value does not imply provider or public/private status.

Add a comment or docstring on `DownloadGrant` stating that `access_mode` describes client retrieval mechanics.

In the frontend branch handling `authenticated_fetch`, add a concise comment explaining that the current bearer token cannot be attached by a plain `<img src>` request.

### Ownership and lifecycle

#### `recipe_image`

Grant access only when:

- `RecipeImage` exists;
- it is linked to a `Recipe`;
- `Recipe.owner_id == current_user.id`;
- `Recipe.status == ACTIVE`.

The related `RecipeResource.status` must not affect authorization. `USED`, `IGNORED`, `UNKNOWN`, and `DELETED` are presentation/editing states, not ownership boundaries.

#### `import_source_image`

Grant access only when:

- `ImportJobSource` exists;
- `ImportJobSource.type == IMAGE`;
- `image_storage_key` is present;
- the parent `ImportJob.owner_id == current_user.id`;
- the parent status is not `FAILED_ARTIFACTS_REMOVED`.

A normal terminal `FAILED` job remains eligible while retained artifacts still exist. Maintenance later clears references and moves it to `FAILED_ARTIFACTS_REMOVED`.

### Database as access-path source of truth

Do not call `HeadObject` before generating an S3 URL.

If a DB row points to a missing physical S3 object, the presigned GET may return `404`. That inconsistency belongs to integrity/orphan maintenance, not the request path.

Tests must prove no HEAD request is performed.

## Required architecture

Create a separate application-layer `MediaAccessService`.

It owns:

- request-order preservation;
- strict resolver dispatch by media reference type;
- domain resolution;
- ownership and lifecycle enforcement;
- normalization to `MEDIA_NOT_FOUND`;
- calling the configured download-access provider;
- partial-success assembly.

Use a strict resolver registry keyed by `MediaReferenceType`.

Do not put domain authorization in:

- API route functions;
- LOCAL/S3 adapters;
- `StorageService`.

Create a separate download-access provider boundary selected at runtime. It receives already-authorized internal media metadata and returns a `DownloadGrant`.

The existing `StorageService` contract remains focused on:

```text
save
read
delete
list_objects
```

You may share provider configuration or an injected boto3 client, but do not add user/domain authorization semantics to `StorageService`.

A reasonable file decomposition is:

```text
backend/app/media/constants.py
backend/app/media/types.py
backend/app/media/queries.py
backend/app/media/access.py
backend/app/media/providers/base.py
backend/app/media/providers/local.py
backend/app/media/providers/s3.py
backend/app/media/providers/runtime.py
backend/app/schemas/media.py
```

Adapt exact names to established project conventions, but preserve the responsibilities and keep files focused.

## Provider behavior

### S3

Generate a presigned GET URL for `StorageLocation.USER_MEDIA`.

Required parameters:

```text
ClientMethod = get_object
Bucket = configured USER_MEDIA bucket
Key = authorized storage key
ExpiresIn = 60
```

Return:

```text
accessMode = direct
expiresAt = signing time + 60 seconds
```

Requirements:

- use UTC-aware timestamps;
- map boto/botocore failures to the project’s stable storage/media operational error and ultimately HTTP `503`;
- never log the generated URL or its signature;
- do not call `HeadObject`;
- preserve lazy boto3 client construction.

### LOCAL

For an authorized reference, return:

```text
url = /media/{media_type}/{media_id}
accessMode = authenticated_fetch
expiresAt = null
```

The GET route must:

1. authenticate the current user;
2. resolve the domain reference again using the same ownership/lifecycle rules;
3. require the runtime provider to be LOCAL;
4. resolve the authorized internal storage key through LOCAL storage;
5. return `FileResponse`;
6. return the same not-found behavior for missing and foreign references.

Do not trust the earlier `POST /media/access` result as permanent authorization.

Remove the current `isinstance(LocalStorageService)` provider switch from the route. Runtime download-access provider selection should own provider behavior.

For an S3 runtime, the authenticated LOCAL GET route must not read or proxy the S3 object. It should fail through a stable unavailable/not-found contract consistent with the final service design and tests. Do not introduce S3 proxying.

## Backend schemas and errors

Create strict Pydantic schemas using existing `CamelModel` conventions.

Expected conceptual types:

```python
class MediaReferenceType(StrEnum):
    RECIPE_IMAGE = "recipe_image"
    IMPORT_SOURCE_IMAGE = "import_source_image"

class DownloadAccessMode(StrEnum):
    DIRECT = "direct"
    AUTHENTICATED_FETCH = "authenticated_fetch"

class MediaAccessReferenceIn(CamelModel):
    type: MediaReferenceType
    id: str

class MediaAccessRequest(CamelModel):
    items: list[MediaAccessReferenceIn]

class DownloadGrant(CamelModel):
    url: str
    expires_at: datetime | None
    content_type: str
    access_mode: DownloadAccessMode

class MediaAccessItemError(CamelModel):
    code: Literal["MEDIA_NOT_FOUND"]
    message: str

class MediaAccessItemOut(CamelModel):
    type: MediaReferenceType
    id: str
    grant: DownloadGrant | None = None
    error: MediaAccessItemError | None = None
```

Ensure `MediaAccessItemOut` validates the exactly-one-of invariant.

Use project error conventions for a provider-wide access failure. Remove obsolete `MEDIA_ACCESS_NOT_AVAILABLE` behavior only after all call sites and tests are replaced.

## Efficient query behavior

Do not perform one SQL query per item.

For each unique reference type:

- collect unique IDs;
- query eligible rows in a bounded batch;
- include ownership and lifecycle predicates in the query where practical;
- return a mapping keyed by public ID.

Preserve original request order when assembling results.

A batch of 100 mixed references must remain bounded by a small fixed number of database queries plus provider grant calls.

## Frontend contract

Replace:

```ts
type RecipeImage = { id: string; mediaUrl: string };
```

with stable references.

A reasonable type model is:

```ts
export type MediaReferenceType = "recipe_image" | "import_source_image";
export type MediaReference = { type: MediaReferenceType; id: string };

export type DownloadGrant = {
  url: string;
  expiresAt: string | null;
  contentType: string;
  accessMode: "direct" | "authenticated_fetch";
};
```

Add `requestMediaAccess(items)` to the API client.

Remove:

- `mediaUrl()`;
- `isApiMediaUrl()`;
- URL-shape-based retrieval decisions;
- old `getMediaBlob(url)` assumptions that every API media URL is protected.

Refactor `AuthenticatedImage` into a domain-reference-based component. Rename it if a clearer name fits the existing code.

The component must accept a stable media reference, not an already constructed URL.

Required behavior:

- request or consume a grant keyed by `(type, id)`;
- `direct`: assign `grant.url` directly to `src`;
- `authenticated_fetch`: fetch with the existing authenticated API client, create an object URL, and revoke it on replacement/unmount;
- handle missing media without breaking sibling images;
- avoid retaining expired direct grants;
- refresh a direct grant when expired or sufficiently close to expiry;
- never infer behavior from URL shape.

Use TanStack Query. Avoid one request per image where several references are already available together:

- recipe grids should batch visible cover references;
- recipe detail should batch its cover/options/images;
- import detail should batch submitted image-source references.

A small reusable batching hook/provider is preferred over embedding separate batch logic into every page.

Default/fallback SVG images remain local static assets and do not need media grants.

Update all affected pages and tests, including at minimum:

- `frontend/src/components/RecipeGrid.tsx`;
- the media image component;
- `frontend/src/pages/RecipeDetailPage.tsx`;
- `frontend/src/pages/ImportJobDetailPage.tsx`;
- API client/types;
- their existing tests.

## Gateway

Replace the old key-shaped endpoint with authenticated entries for:

```text
POST /media/access
GET /media/{media_type}/{media_id}
```

Both are non-public.

Update gateway validation tests and run `make gateway-check`.

## Documentation

Create `docs/media-access.md`.

It must independently document:

- stable media IDs versus storage keys and access URLs;
- the complete client flow;
- request/response examples;
- partial-success semantics;
- missing/foreign indistinguishability;
- `DownloadAccessMode`;
- why `accessMode` is not `requiresAuth`;
- LOCAL behavior;
- S3 behavior and 60-second expiry;
- DB-authoritative access resolution and no `HeadObject`;
- frontend responsibilities;
- logging/security restrictions;
- `DownloadGrant != UploadIntent`;
- deferred upload/CDN/infrastructure work.

Update other documentation whose P9/P10 boundary becomes stale, especially:

- `docs/s3-storage.md`;
- `docs/architecture/production-roadmap.md`;
- `docs/implementation-plan.md`;
- relevant README/API documentation.

Do not duplicate contradictory contracts across documents.

## Required tests

Follow TDD for each meaningful unit. Add focused tests before implementation and verify they fail for the expected reason.

### Backend service/query tests

Cover:

- recipe image owned by active recipe -> grant;
- foreign recipe image -> `MEDIA_NOT_FOUND`;
- missing recipe image -> identical `MEDIA_NOT_FOUND`;
- inactive/deletion-pending recipe -> `MEDIA_NOT_FOUND`;
- related resource status does not affect access;
- valid import image source -> grant;
- foreign import source -> `MEDIA_NOT_FOUND`;
- non-image source -> `MEDIA_NOT_FOUND`;
- null storage key -> `MEDIA_NOT_FOUND`;
- `FAILED` parent remains eligible;
- `FAILED_ARTIFACTS_REMOVED` parent is denied;
- mixed batch partial success;
- request order preservation;
- duplicate-position preservation;
- bounded query count or equivalent proof against N+1 behavior.

### API tests

Cover:

- authentication required;
- 1-item request;
- mixed request;
- empty request -> `422`;
- 101 items -> `422`;
- unsupported type -> `422`;
- extra fields -> `422`;
- provider-wide failure -> `503`;
- public domain responses contain IDs and no `mediaUrl`/storage key;
- missing and foreign per-item responses are indistinguishable.

### S3 provider tests

Extend the injected recording client or use botocore Stubber.

Cover:

- exact `generate_presigned_url` call;
- `ExpiresIn=60`;
- `get_object` parameters contain the correct USER_MEDIA bucket/key;
- UTC expiry;
- no HEAD call;
- lazy client reuse;
- SDK failure mapping;
- URL is not logged.

### LOCAL route tests

Cover:

- valid owner receives exact bytes and content type;
- missing reference;
- foreign reference;
- recipe lifecycle denial;
- import lifecycle denial;
- unsafe or malformed storage key cannot escape the configured root;
- S3 runtime does not proxy/read the object;
- route contains no storage key.

### Frontend tests

Cover:

- API batch serialization/deserialization;
- visible references are batched;
- ordered results are matched by `(type, id)`;
- `direct` uses URL without blob fetch;
- `authenticated_fetch` uses the authenticated API client;
- object URL creation and revocation;
- one failed item does not suppress successful siblings;
- fallback image behavior;
- expired direct grant refresh;
- no URL-shape branching;
- recipe grid, detail, cover preview/modal, and import source images continue to render.

### Gateway and boundary tests

Cover:

- new routes exist and are authenticated;
- old key route is absent;
- public schemas contain no storage key or `mediaUrl`;
- provider-specific modules do not own domain queries;
- `StorageService` has not gained domain/user authorization methods.

## Verification commands

Run from repository root unless noted.

Backend:

```bash
cd backend
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Frontend:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test:ci
pnpm build
```

Gateway:

```bash
make gateway-check
```

Also run the clean PostgreSQL migration check used by CI, even though no migration is expected:

```bash
cd backend
uv run alembic upgrade head
uv run alembic current
```

## Manual smoke tests

Perform and record these separately from automated tests.

### LOCAL / PREVIEW

Through KrakenD, not direct FastAPI diagnostics:

1. Open a recipe list containing covers.
2. Open recipe detail.
3. Open source-image preview/modal.
4. Open an import job with submitted image sources.
5. Confirm browser requests `POST /media/access`.
6. Confirm LOCAL grants use `authenticated_fetch`.
7. Confirm the subsequent GET route contains media type and ID, not a storage key.
8. Confirm the GET carries application authentication.
9. Confirm another user's media ID does not reveal existence.
10. Confirm an import in `FAILED` can display retained source images.
11. Run failed-import artifact cleanup and confirm `FAILED_ARTIFACTS_REMOVED` sources no longer receive grants.

### S3 provider smoke

Use a private non-production test bucket and test identity.

1. Start the backend with S3 configuration.
2. Request grants for owned recipe and import media.
3. Confirm grants use `direct`.
4. Confirm URLs expire in approximately 60 seconds.
5. Confirm the browser loads the image directly from S3.
6. Confirm the URL is absent from application logs.
7. Confirm a foreign/missing ID produces `MEDIA_NOT_FOUND`.
8. Confirm a DB reference to a missing S3 object still receives a signed URL and the subsequent GET returns provider `404`, proving no HEAD check.
9. Confirm no S3 credentials or bucket names appear in public API responses.

If a live S3 smoke cannot be executed, state the exact reason in the PR and list the automated provider coverage. Do not claim it was run.

## Git and PR requirements

Create a dedicated implementation branch from the current `main`, for example:

```text
codex/presigned-media-access
```

Do not implement on the documentation branch.

Use small, intentional commits with tests included. Do not squash unrelated changes into P10.

Open a draft PR against `main`.

PR body must include:

```text
## Scope
## Explicitly deferred
## Automated verification
## Manual verification
## Verification gaps
## Security notes
```

Do not merge the PR. Leave final review and merge to the user.

## Completion report

At the end, report:

- branch and PR;
- files added/changed;
- exact API contract implemented;
- automated commands with pass counts;
- manual smoke results;
- any verification gaps;
- confirmation that storage keys and `mediaUrl` are absent from public responses;
- confirmation that no HEAD request is used;
- confirmation that access-mode comments and `docs/media-access.md` were added;
- deferred work unchanged.

Do not state that work is complete unless every claimed check has fresh evidence.
