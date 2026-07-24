# P10 — Presigned Media Access: Instructions for Codex

You are implementing P10 in `starkovalera/recipe-manager`.

Use the current repository state as the source of truth. Read the affected code, tests, and these authoritative documents before editing:

- `docs/superpowers/specs/2026-07-24-presigned-media-access-design.md`
- `docs/s3-storage.md`
- `docs/maintenance-processing.md`
- `docs/architecture/production-roadmap.md`

Do not change the approved architecture or expand scope without a real blocker.

## Autonomous execution workflow

Perform one readiness check at the beginning. Verify that you have repository and `origin` access, the intended `main` base, the required documents, a usable working tree, and the tools needed to install dependencies from committed lockfiles.

Ask the user only when continuing would require guessing or violating the approved design. Valid blockers are limited to:

- a literal contradiction between the approved design and the current repository;
- a material ambiguity with different architecture, security, public-contract, migration, or scope consequences;
- a missing prerequisite controlled by the user, such as credentials, an account, a private test bucket, a key, or a cloud-console action;
- a required scope expansion;
- a destructive or irreversible action that was not already authorized.

Routine implementation choices are not blockers.

If the readiness check passes, begin immediately. Do not ask the user to approve an implementation plan, branch name, task breakdown, file choices, tests, commits, refactors inside the approved scope, or each next step.

Autonomously:

1. update repository refs and confirm `main` as the base;
2. create a dedicated feature branch, normally `codex/presigned-media-access`;
3. inspect relevant code and tests;
4. implement the complete phase;
5. run all automated verification and self-audits;
6. update documentation and required comments;
7. commit and push intentional changes;
8. open a draft PR against `main`;
9. provide one consolidated completion and verification report.

Progress updates are allowed, but they are not approval gates. The user reviews the complete draft PR, not every substep. Do not merge the PR.

## Goal

Replace storage-key-based browser media access with stable domain media references and provider-specific download grants for LOCAL and S3 storage.

```text
domain response
→ stable media reference (type + id)
→ POST /media/access
→ per-item grant or MEDIA_NOT_FOUND
→ frontend retrieves according to accessMode
```

## In scope

- `recipe_image` references backed by `RecipeImage.id`;
- `import_source_image` references backed by `ImportJobSource.id`;
- authenticated batch `POST /media/access`, 1–100 items;
- partial-success response semantics;
- S3 presigned GET with a 60-second TTL;
- authenticated LOCAL retrieval by media type and domain ID;
- frontend support for `direct` and `authenticated_fetch`;
- removal of public `mediaUrl`, storage-key URLs, URL-shape routing, `build_media_url()`, and the legacy key-based media route;
- gateway changes;
- backend, frontend, gateway, and boundary tests;
- `docs/media-access.md` and updates to stale P9/P10 documentation;
- required explanatory comments.

## Explicitly deferred

Do not implement upload grants, direct browser upload, `UploadIntent`, a generic `Media` or `StorageObject` table, `HeadObject` checks, CDN/CloudFront, public sharing, Terraform/IAM/bucket provisioning, multipart upload, persistent grants, S3 proxying through FastAPI, or unrelated UI redesign.

No database migration is expected because both stable IDs already exist. Stop and explain before adding one.

## Public API contract

Public domain responses expose stable IDs only:

- `RecipeImageOut` keeps `id` and removes `mediaUrl`;
- `ImportJobSourceOut` exposes its own `id`;
- no public schema or frontend type exposes storage keys, bucket names, provider locators, or local paths.

Remove the old route:

```text
GET /media/{namespace}/{kind}/{owner_id}/{entity_id}/{object_name}
```

Add authenticated routes:

```text
POST /media/access
GET /media/{media_type}/{media_id}
```

The GET route must never accept a storage key from the client.

### Request

```json
{
  "items": [
    {"type": "recipe_image", "id": "image-id"},
    {"type": "import_source_image", "id": "source-id"}
  ]
}
```

Rules:

- minimum 1 and maximum 100 items;
- strict reference type enum;
- extra fields rejected;
- input order preserved;
- duplicate positions preserved;
- internal resolution may deduplicate repeated references.

### Response

A structurally valid batch returns HTTP `200` even when some items are inaccessible. Each item repeats `type` and `id` and contains exactly one of `grant` or `error`.

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

Use identical `MEDIA_NOT_FOUND` item errors for missing, foreign, lifecycle-ineligible, detached, malformed-domain, and unusable-metadata references. Never disclose that a foreign record exists.

Batch-level responses:

- `401` for invalid or missing authentication;
- `422` for malformed input, unsupported type, empty batch, extra fields, or more than 100 items;
- `503` for provider-wide grant-generation failure.

Do not duplicate a provider-wide failure inside every item.

## Download grant and access modes

`DownloadGrant` contains:

```text
url
expiresAt
contentType
accessMode
```

`expiresAt` is UTC and nullable. S3 returns an expiry; LOCAL returns `null`.

Define:

```text
direct
authenticated_fetch
```

`accessMode` describes client retrieval mechanics only. It is not a provider enum, `requiresAuth` flag, or public/private classification.

- `direct`: the URL may be assigned directly to `<img src>` or another browser resource attribute.
- `authenticated_fetch`: the URL must be fetched through the authenticated API client, converted to a `Blob`, and exposed through an object URL.

Add comments on both enum values explaining browser behavior and warning that the values do not imply provider or public/private status. Add a comment/docstring on `DownloadGrant.access_mode`. Add a frontend comment explaining that the current bearer token cannot be attached by a plain `<img src>` request.

## Ownership and lifecycle

### `recipe_image`

Grant access only when the image exists, is linked to a recipe, the recipe belongs to the current user, and `Recipe.status == ACTIVE`.

A related `RecipeResource.status` must not affect authorization. `USED`, `IGNORED`, `UNKNOWN`, and `DELETED` remain presentation/editing states.

### `import_source_image`

Grant access only when the source exists, `type == IMAGE`, `image_storage_key` is present, the parent import belongs to the current user, and the parent status is not `FAILED_ARTIFACTS_REMOVED`.

A terminal `FAILED` job remains accessible while retained artifacts exist. Cleanup later clears references and moves it to `FAILED_ARTIFACTS_REMOVED`.

## Required architecture

Create a separate application-layer `MediaAccessService` with a strict resolver registry keyed by media reference type.

It owns request-order preservation, batch resolution, ownership/lifecycle enforcement, not-found normalization, provider invocation, and partial-success assembly.

Do not place domain authorization or domain queries in API routes, LOCAL/S3 providers, or `StorageService`.

Create a separate runtime-selected download-access provider boundary. It receives already-authorized internal metadata and returns a grant. Keep `StorageService` focused on storage operations such as save/read/delete/list.

Resolve unique IDs in bounded batches by type. Do not issue one SQL query per item. Preserve original request positions when assembling results.

## Provider behavior

### S3

Generate a presigned URL with:

```text
ClientMethod = get_object
Bucket = configured USER_MEDIA bucket
Key = authorized storage key
ExpiresIn = 60
accessMode = direct
expiresAt = signing time + 60 seconds
```

Use UTC-aware timestamps, preserve lazy client construction/reuse, map SDK failures to the project’s stable operational error and HTTP `503`, and never log the URL or signature.

Do not call `HeadObject`. The database is the access-path source of truth. A missing physical object may produce a signed URL whose GET returns S3 `404`.

### LOCAL

Return:

```text
url = /media/{media_type}/{media_id}
accessMode = authenticated_fetch
expiresAt = null
```

The GET route authenticates the user and resolves the reference again using the same ownership/lifecycle rules before returning `FileResponse`. It must use LOCAL storage safely and must not proxy S3 bytes when the runtime provider is S3.

Remove route-level `isinstance(LocalStorageService)` switching. Provider selection belongs to the runtime boundary.

## Frontend

Replace URL-based media types with stable `{type, id}` references. Add a batch API client and reusable TanStack Query-based grant loading/cache.

- recipe grids batch visible cover references;
- recipe detail batches hero, cover options, and source images;
- import detail batches submitted image sources;
- `direct` uses the URL directly;
- `authenticated_fetch` uses the authenticated API client and revokes object URLs on replacement/unmount;
- expired direct grants are refreshed;
- one failed item does not suppress successful siblings;
- default SVG assets remain local and require no grant;
- no behavior may depend on URL shape or provider name.

Remove `mediaUrl()`, `isApiMediaUrl()`, and legacy protected-URL assumptions.

## Gateway and documentation

Configure both new routes as authenticated and remove the legacy key route. Update gateway tests and run `make gateway-check`.

Create `docs/media-access.md` documenting stable IDs versus storage keys/access URLs, request/response examples, partial success, missing/foreign indistinguishability, both access modes, why this is not `requiresAuth`, LOCAL/S3 behavior, TTL, no-HEAD policy, frontend responsibilities, logging restrictions, and `DownloadGrant != UploadIntent`.

Update stale roadmap, S3, implementation-plan, README, or API documentation without creating contradictory contracts.

## Required automated coverage

Cover at minimum:

- request validation, order, duplicates, partial success, and provider-wide `503`;
- identical missing/foreign behavior;
- recipe ownership, active status, detached images, and resource-status independence;
- import ownership, image type, storage-key presence, `FAILED`, and `FAILED_ARTIFACTS_REMOVED`;
- bounded query count;
- exact S3 presign parameters, UTC expiry, lazy client reuse, no HEAD, SDK failures, and no URL logging;
- LOCAL bytes/content type, repeated authorization, unsafe key containment, and no S3 proxying;
- frontend batching, direct mode, authenticated fetch, object URL cleanup, fallback behavior, partial failures, expiry refresh, and no URL-shape branching;
- gateway routes and absence of public storage keys/`mediaUrl`;
- architecture-boundary tests where appropriate.

Follow TDD for meaningful units.

## Mandatory self-audit

Before asking for human review, run and report:

```bash
git fetch origin
git diff --check origin/main...HEAD
git diff --stat origin/main...HEAD
git diff --name-only origin/main...HEAD
git log --oneline origin/main..HEAD
```

Group every changed file by backend, frontend, gateway, docs, and tests. Explain every unexpected file and confirm whether migrations, Terraform, unrelated queue/Lambda/auth code, or the UI/UX workspace changed.

Run and classify every match:

```bash
rg "mediaUrl|media_url|build_media_url|isApiMediaUrl|/media/\{namespace\}|legacy-media" backend frontend infra docs
rg "storage_key|storageKey" backend/app/schemas frontend/src
rg "head_object|HeadObject|head_calls" backend/app backend/tests
rg "requiresAuth|requires_auth" backend frontend docs
rg "isinstance\(.*LocalStorageService" backend/app
```

Prove that production code has no legacy flow, public storage keys, HEAD-per-grant call, `requiresAuth` substitution, or route-level provider switch.

Provide exact file paths and class/function names for the service, resolver registry, ownership queries, runtime provider selection, LOCAL route/provider, S3 provider, frontend grant layer, gateway entries, and required comments.

Finish with a 6–10 item table:

```text
Decision | File | Class/function or line range | What the user should inspect
```

Do not ask the user to scan every changed file or classify repository-wide searches manually.

## Verification commands

Run with fresh evidence:

```bash
cd backend
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run alembic upgrade head
uv run alembic current

cd ../frontend
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test:ci
pnpm build

cd ..
make gateway-check
```

Report pass counts, skips, warnings, failures, and exact reasons for anything not run.

## Manual and external verification handoff

The user owns browser-based LOCAL/PREVIEW checks and AWS-account actions. Do not claim them without direct evidence.

Keep `docs/handoffs/p10-presigned-media-access-owner-runbook.md` accurate. Provide the implementation branch SHA and prerequisites. Never ask the user to mutate database state manually for edge cases already covered by automated tests.

Live S3 verification requires a user-supplied private test bucket and credentials. Record it as a verification gap when unavailable.

## Git and PR requirements

Create the feature branch from current `main`, use intentional commits, push it, and open a draft PR against `main`. Do not implement on the documentation branch and do not merge.

PR body sections:

```text
## Scope
## Explicitly deferred
## Automated verification
## Diff and architecture audit
## Manual verification
## Verification gaps
## Security notes
## Key human review map
```

At completion, report the branch and PR, exact contract, automated evidence, classified searches, architecture/security audit, key human-review map, manual results, verification gaps, and confirmations that public storage keys/`mediaUrl` and HEAD access are absent.

Never claim completion without fresh evidence.