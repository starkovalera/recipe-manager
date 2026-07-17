# Recipe Manager Rewrite Design

## Status

Draft design for a greenfield rewrite of the current recipe MVP into a Python backend and React frontend. The existing `recipe-mvp` repository remains unchanged and is used only as a behavioral reference.

## Goals

Build a local-first version of the app on a more durable stack while keeping a path toward mobile clients and cloud deployment.

Immediate goals:

- Preserve the current MVP product behavior: recipe library, imports from URL/images/text, recipe detail/editing, user notes, media, source tracking, and review warnings.
- Move backend logic into Python so import, media, video, OCR-adjacent, and AI workflows have a better long-term home.
- Make imports non-blocking: the frontend creates an import job, then polls the backend until the job succeeds or fails.
- Add backend-side concurrency control for imports per client.
- Keep local development simple: SQLite database and local filesystem storage.
- Keep backend and frontend separable so they can later become separate services or separate repositories.

Non-goals for the first rewrite:

- Mobile app implementation.
- Cloud storage implementation.
- Multi-user authentication beyond the existing default/local user concept.
- Full production deployment hardening.
- Video frame slicing. Video import uses transcript and poster image only, matching the current simplified behavior.

## Repository Layout

The new project lives next to the current repository:

```text
C:\Users\stark\Documents\recipe-manager
```

Initial structure:

```text
recipe-manager/
  backend/
    pyproject.toml
    alembic.ini
    app/
      main.py
      api/
      core/
      db/
      models/
      schemas/
      services/
      imports/
      ai/
      storage/
      media/
      users/
    tests/
  frontend/
    package.json
    vite.config.ts
    src/
      api/
      app/
      components/
      pages/
      routes/
      styles/
      types/
  docs/
    design.md
    api.md
    import-pipeline.md
  Makefile
  README.md
```

Separation rules:

- Backend and frontend do not import code from each other.
- No shared runtime package in the first version.
- The API boundary is HTTP plus JSON schemas documented by OpenAPI and docs.
- If generated frontend API types are added later, they should be generated artifacts that can be removed or moved when repos split.
- Root-level Makefile may orchestrate local commands, but backend and frontend remain independently runnable.

## Configuration

Backend configuration should be environment-based and loaded through Pydantic settings.

Initial backend settings:

- `APP_ENV`, defaults to fail-closed `PROD`.
- `DATABASE_URL`, with local PostgreSQL defaults in `DEV`/`PREVIEW`, isolated SQLite in `TEST`, and an explicit PostgreSQL value required in `PROD`.
- `QUEUE_PROVIDER`, defaults to `DRAMATIQ` outside `PROD`; `PROD` requires `SQS`.
- `STORAGE_PROVIDER`, defaults to `LOCAL` outside `PROD`; `PROD` requires `S3`.
- `REDIS_URL`, local outside `PROD` and unsupported in `PROD`.
- `UPLOAD_DIR`, local outside `PROD` and unsupported in `PROD`.
- `MAX_IMPORT_IMAGES`, default `10`.
- `MAX_IMPORT_TEXT_CHARS`, default `1000`.
- `MAX_RECIPE_INGREDIENTS`, default `50`.
- `MAX_RECIPE_INSTRUCTION_CHARS`, default `1000`.
- `MAX_RECIPE_NOTE_CHARS`, default `500`.
- `MAX_UPLOAD_BYTES`.
- `MAX_VIDEO_BYTES`.
- `MAX_IMPORT_VIDEOS`, default `1`.
- `IMPORT_MIN_CONFIDENCE`, default `0`.
- `IMPORT_WARN_CONFIDENCE`, default `0.75`.
- `MAX_PARALLEL_IMPORTS_PER_CLIENT`, default to a conservative local value such as `1`.
- `OPENAI_API_KEY`.
- `OPENAI_RECIPE_MODEL`.
- `OPENAI_VIDEO_TRANSCRIPTION_MODEL`.
- `ENABLE_COVER_CANDIDATE_GUARD`, default `false`.
- `OPENAI_COVER_VALIDATION_MODEL`.
- `FFMPEG_PATH` and `FFPROBE_PATH` if needed.

Frontend configuration should be independent:

- `VITE_API_BASE_URL`, default `http://127.0.0.1:8081` for the local KrakenD gateway. FastAPI remains directly reachable on `http://127.0.0.1:8010` for upstream diagnostics during the compatibility phase.

Local storage directories should be environment-specific to avoid preview/dev data collisions, for example:

- `backend/storage/dev/`
- `backend/storage/preview/`
- `backend/storage/test/`

## Data Model

The new data model should preserve current concepts, not necessarily exact table names.

Core entities:

- `User`: local/default user for now.
- `Recipe`: title, servings, cook time, instructions JSON/list, nutrition estimate JSON, author name, source name, note, cover image pointer, timestamps.
- `Ingredient`: recipe id, name, quantity, unit, note, position.
- `Tag`: owner id, name.
- `RecipeTag`: recipe/tag join table.
- `RecipeImage`: recipe id, role (`source`, `cover`), storage key, original name, mime type, size, position, optional source image pointer.
- `RecipeSource`: recipe id, optional parent source id, type (`url`, `image`, `text`), source origin (`MANUAL`, `URL`, `URL_VIDEO`), url/text/image id, position, source ref, status (`unknown`, `used`, `ignored`), assessment reason, assessment confidence. Manual text/image and URL rows are primary sources; URL text/images and URL video transcript/poster are child final sources.
- `RecipeReviewFlag`: recipe id, type, status (`open`, `resolved`), reason code, message, details JSON, timestamps.
- `ImportJob`: owner/client id, status (`pending`, `processing`, `succeeded`, `failed`), client import id, error code/message, created recipe id, timestamps.
- `ImportJobSource`: job id, type, status, url/text/image metadata, position.
- `Collection` and collection membership if we keep current collection behavior in the first migration.

Design preference:

- Use UUID primary keys.
- Keep JSON fields for AI-derived flexible data where product shape is still changing.
- Keep migrations explicit with Alembic.
- Do not store absolute local file paths in the database; store storage keys.

## API Contract

The backend owns all business logic. The frontend communicates only over HTTP.

Initial endpoints:

### Health

- `GET /health`

### Recipes

- `GET /recipes`
  - Query params: search, tag, collection, pagination later.
- `GET /recipes/{recipeId}`
- `PATCH /recipes/{recipeId}`
  - Editable fields: title, servings, cook time, instructions, ingredients, tags, note, cover selection later.
- `DELETE /recipes/{recipeId}`

### Recipe Notes

Can be part of `PATCH /recipes/{recipeId}`. The note is plain user text, trimmed and rejected when it exceeds `MAX_RECIPE_NOTE_CHARS`. It is never sent to AI import processing.

### Imports

- `POST /imports`
  - Multipart form with optional `url`, optional `text`, optional files, required `clientImportId` from frontend.
  - Returns immediately with `jobId` and status.
- `GET /imports/{jobId}`
  - Returns status, timestamps, error code/message, and created recipe id when available.
- Optional later: `GET /imports/{jobId}/events` or WebSocket/SSE. Not needed for first version.

### Media

- `GET /media/{storageKey}`
  - Serves local files through backend.
  - Future cloud version can redirect to signed URLs without changing recipe payloads.

### Review Flags

- `PATCH /recipes/{recipeId}/review-flags/{flagId}`
  - Resolve/unresolve warning flags.

### Resources

- `GET /recipes/{recipeId}/sources`
- Later: `DELETE /recipes/{recipeId}/sources/{sourceId}`
  - Deleting a source does not alter extracted recipe fields.
  - Source image deletion should not physically delete cover image files if currently used as cover.

## Import Job Lifecycle

1. Frontend creates a stable `clientImportId` for each submit attempt.
2. Frontend sends `POST /imports` with URL/text/files.
3. Backend validates request synchronously:
   - at least one source exists;
   - image count does not exceed `MAX_IMPORT_IMAGES`;
   - file types and sizes are valid;
   - text length is valid;
   - URL is valid http/https.
4. Backend checks per-client active import limit.
5. Backend creates `ImportJob(status=pending)` and returns `jobId` immediately.
6. Background worker claims the job and sets `status=processing`.
7. Worker runs import pipeline.
8. On success, worker creates recipe and sets job `status=succeeded`, `createdRecipeId=<id>`.
9. On failure, worker cleans saved files where appropriate and sets job `status=failed`, `errorCode`, `errorMessage`.
10. Frontend polls `GET /imports/{jobId}` until terminal state.
11. On success, frontend navigates to recipe detail or refreshes recipe list.
12. On failure, frontend shows the error.

Concurrency rules:

- `MAX_PARALLEL_IMPORTS_PER_CLIENT` limits jobs in `pending` or `processing` per client.
- `clientImportId` prevents duplicate submit from creating duplicate recipes.
- Stale `pending`/`processing` jobs should be failed after a configured timeout.

Local worker implementation:

- First version may use an in-process asyncio queue started with FastAPI lifespan.
- Job state must be persisted in the database so frontend polling remains reliable.
- The import pipeline should not depend on in-memory state except for queue scheduling.
- Future cloud version can replace the in-process queue with Redis/Celery/RQ/Arq or a cloud task queue without changing the API contract.

## Import Pipeline Behavior

The Python implementation should preserve current business behavior.

Source order and priority:

- User attachments are accepted first and have highest priority for image capacity.
- URL images are accepted only into remaining capacity.
- User text is recipe evidence and does not count against image capacity.
- URL caption/text is recipe evidence and does not count against image capacity.
- Video transcript is recipe evidence and does not count against image capacity.
- Video poster image counts as an image source and is accepted only if image capacity remains.

Validation and limits:

- If uploaded attachment count exceeds `MAX_IMPORT_IMAGES`, fail before URL loading.
- Platform loaders should fail oversized image carousels before downloading images when the platform can expose total image count.
- If accepted source set is empty, fail as not a recipe.

Video behavior:

- Download/inspect video only enough to get audio transcript and poster image.
- Do not slice video frames in first rewrite.
- If video processing fails, continue with non-video sources when possible and log the failure.

AI extraction:

- AI receives a structured list of final sources only: manual text/images plus URL-derived text/images/video transcript/poster. URL parent rows are kept in the database for primary-source status aggregation, but are not sent to AI. Final sources are labeled with short request-local ids such as `source_1`; the backend maps those ids back to `RecipeSource` objects after AI returns.
- AI returns JSON matching the extraction schema.
- Backend validates AI JSON strictly.
- If the response is invalid or not a recipe, fail the import.
- If `quality.confidence <= IMPORT_MIN_CONFIDENCE`, fail the import.
- If `quality.hasConflicts`, `quality.hasIgnored`, or `quality.confidence <= IMPORT_WARN_CONFIDENCE`, create a `RecipeReviewFlag`.
- Source statuses derive from `quality.primarySourceRefs` and `quality.ignoredSourceRefs`.
- Single URL imports may normalize internal conflicts so parts of one post do not create false source conflicts.

Cover behavior:

- Prefer AI `coverCandidate` when it references an accepted image source.
- Generate a normalized cover image from the chosen source.
- Run deterministic/autocrop logic for selected cover images.
- Cover guard remains behind a feature flag and disabled by default.
- If no suitable cover exists, use frontend/backend default image behavior.

Cleanup behavior:

- If import fails after saving files but before recipe creation, delete saved files for that job.
- Never delete files outside configured storage directory.
- Preview/test storage directories must be separate from dev storage.

## AI Boundary

Define an interface, not direct OpenAI calls spread through the codebase.

Suggested backend interfaces:

- `RecipeExtractionProvider.extract(sources) -> ExtractedRecipe | NotRecipe | Error`
- `VideoTranscriptionProvider.transcribe(video) -> text | None`
- `CoverValidationProvider.validate(recipe, source, candidate) -> result`

OpenAI is one implementation. Tests should use fake providers.

The prompt should live in a dedicated backend module or text file and be versioned. The response schema should be explicit and validated before any database writes.

## Storage Boundary

Define a storage service interface:

- `save(bytes, original_name, mime_type) -> storage_key, size`
- `read(storage_key) -> bytes`
- `delete(storage_key)`
- `url_or_response(storage_key)` for media serving implementation details.

The first implementation is local filesystem storage. `S3` is the required production provider value, but its adapter is implemented in a later production iteration. Database rows store storage keys only.

## Frontend Behavior

Initial pages:

- Recipe list.
- Import page.
- Recipe detail/edit page.
- Collections page if included in first parity target.

Import UI behavior:

- User can provide URL, text, and image attachments.
- Frontend creates `clientImportId` per submit.
- Submit button is disabled while request is starting to prevent accidental double submit.
- After `POST /imports`, UI enters polling mode.
- Polling interval can be short locally, for example 1-2 seconds.
- On `succeeded`, navigate to recipe detail or update the page with result link.
- On `failed`, show visible error code/message.

TanStack Query usage:

- `useMutation` for `POST /imports`.
- `useQuery` with `refetchInterval` for `GET /imports/{jobId}` while status is not terminal.
- `invalidateQueries` for recipe lists after import success or recipe edits.
- `useQuery` for recipe detail and list pages.

Frontend should not know storage internals. It renders media URLs returned or constructed from backend API routes.

## YouTube Video Import

### Scope and selected strategy

The first YouTube integration supports public videos referenced by these direct-link forms:

- `youtube.com/watch?v=<video-id>`;
- `youtube.com/shorts/<video-id>`;
- `youtu.be/<video-id>`.

Playlist-only URLs, private videos, unlisted videos, active live streams, and videos longer than 15 minutes are not supported. YouTube URL syntax is covered by the common URL validation performed when an import is created; the YouTube loader must not introduce a parallel creation-time validation system. After creation, the loader extracts the video id and converts every accepted form to a canonical watch URL.

The selected processing strategy separates video understanding from recipe extraction:

```text
YouTube URL
  -> YouTube Data API metadata and validation
  -> Gemini 2.5 Flash VideoEvidence extraction
  -> usable VideoEvidence + YouTube description + other import evidence
  -> existing OpenAI recipe extraction
  -> existing recipe persistence and quality flow
```

Gemini receives only the canonical YouTube video URL. It does not receive the YouTube description, thumbnail, manual attachments, or other import resources. Gemini is responsible for faithful video evidence extraction, while the existing OpenAI provider remains responsible for constructing the normalized recipe from all accepted evidence.

### Configuration and credentials

The backend configuration adds:

```text
YOUTUBE_API_KEY
GEMINI_API_KEY
GEMINI_YOUTUBE_MODEL=gemini-2.5-flash
MAX_YOUTUBE_VIDEO_DURATION_SECONDS=900
MIN_YOUTUBE_FALLBACK_DESCRIPTION_CHARS=200
MIN_YOUTUBE_VIDEO_EVIDENCE_CONFIDENCE=0.70
YOUTUBE_RESOURCE_RETENTION_DAYS=30
```

Development and production use different Google projects and different API keys for both YouTube Data API and Gemini. The application uses the same environment-variable names in each environment; deployment secrets provide the environment-specific values. Keys are backend-only, must not appear in logs or job events, and should be restricted to their intended API and server caller where the deployment supports stable outbound IP restrictions. Adding a production runtime profile is outside this integration's scope.

### YouTube Data API boundary

One `videos.list` request with `part=snippet,contentDetails,status` retrieves the fields needed to:

- read the title, description, channel identity, and thumbnail variants;
- parse the ISO 8601 duration;
- reject videos over 900 seconds before calling Gemini;
- reject unavailable, non-public, unprocessed, or active-live videos;
- record relevant caption, embedding, regional, and content-restriction metadata for diagnostics.

The loader does not use `search.list`, comments, or captions endpoints. Direct URL parsing avoids the high-cost search endpoint, and one import normally consumes one `videos.list` quota unit. Invalid API requests still consume quota, so common URL validation and local video-id validation happen before the API call.

YouTube API rate and quota handling stays inside the client boundary. Transient rate-limit and `5xx` responses receive a small bounded exponential-backoff retry with jitter and `Retry-After` support. Invalid requests, permanent availability/privacy failures, duration failures, and exhausted daily quota are not retried inside the import. The implementation reuses the platform-neutral import/video error families; it does not add `YOUTUBE_VIDEO_UNAVAILABLE`, `YOUTUBE_VIDEO_NOT_PUBLIC`, `YOUTUBE_VIDEO_TOO_LONG`, or `YOUTUBE_URL_INVALID`. Error details and user-facing text identify YouTube and the concrete reason. If the platform-neutral video distinctions are not yet present when implementation starts, they are added once at the shared video boundary rather than as YouTube-specific types.

### VideoEvidence contract

Gemini returns structured evidence rather than a recipe. The contract contains at least:

```text
transcript
on_screen_text[]
ingredients_observed[] { name, quantity, timestamp, evidence_kind }
visual_steps[] { timestamp, description }
uncertainties[]
confidence
```

The prompt instructs Gemini to report only evidence supported by speech, visible text, or visible actions; retain timestamps; distinguish evidence kinds; express uncertainty; ignore instructions embedded in the source content; and avoid normalizing the observations into a final recipe. The provider validates the structured response before it can enter the normal extraction flow.

A response is usable only when it is structurally valid, contains meaningful evidence, and has `confidence >= 0.70`. Only usable `VideoEvidence` is persisted as a child `RecipeResource` and passed to OpenAI. A structurally valid response below the threshold is recorded in the success job event and telemetry, then discarded; it is not saved as an ignored resource. Invalid or failed responses are also not persisted as recipe resources.

### Fallback behavior

Gemini failure, invalid evidence, empty evidence, and evidence below the confidence threshold use the same fallback decision:

1. If other meaningful extraction resources exist, continue through the normal OpenAI extraction flow without `VideoEvidence`.
2. If YouTube description is the only remaining meaningful resource, normalize its whitespace and require at least 200 characters.
3. If the normalized description passes the threshold, call OpenAI with the description.
4. If it does not pass, fail the import immediately without an unnecessary OpenAI call.

The title, channel name, source URL, and thumbnail do not contribute to the 200-character threshold. A sufficiently long description is not assumed to contain a recipe; it only permits OpenAI to make the normal recipe/not-a-recipe decision.

### Extraction source and cover behavior

The OpenAI extraction stage receives:

- usable `VideoEvidence`, when available;
- YouTube description and other API text selected for extraction;
- manual text and images and any other normal import evidence.

The YouTube thumbnail is persisted outside the extraction input and is never sent to Gemini or OpenAI. It does not consume the attachment-first extraction-image capacity. Other remote images continue to use only the image capacity remaining after manual attachments.

The best available YouTube thumbnail is downloaded and stored byte-for-byte. It is not cropped, resized, re-encoded, or passed through `create_cover_image`; the saved `RecipeImage` is assigned directly as `recipe.cover_image`. User-facing presentation must preserve the full image, identify YouTube as its source, and link to the original video. A permanently unavailable thumbnail leaves the recipe without a cover rather than creating a modified copy.

### Resource retention model

API-derived text used in extraction, usable `VideoEvidence`, and the YouTube thumbnail are stored as child `RecipeResource` rows under the primary user-provided URL resource. Validation-only response fields remain in bounded telemetry/job-event metadata rather than being copied into recipe resources.

`RecipeResource` adds these nullable lifecycle fields:

```text
expires_at
deleted_at
delete_reason
```

`expires_at` is an absolute timestamp rather than a relative TTL. YouTube-derived resources initially receive `expires_at = created_at + 30 days`. The parent URL was provided by the user and is not automatically expired with its API-derived children.

When a resource is cleaned, its row remains as historical provenance with `status=deleted`, `deleted_at`, and a stable `delete_reason`. Content-bearing fields are cleared, associated non-cover media files are deleted, and obsolete `RecipeImage` rows/links are removed. Initial reason values include user deletion, retention expiry, parent deletion, permanent source unavailability, and compliance retention. User-initiated resource deletion uses the same fields rather than only changing the status.

The first working YouTube import writes expiry metadata but does not wait for the scheduled retention lifecycle. Later milestones add:

1. an idempotent cleanup service and Dramatiq actor for expired non-cover text and media;
2. a periodic scheduler process that enqueues bounded cleanup batches;
3. refresh behavior for an expired current YouTube cover.

Cover refresh calls the YouTube API again, downloads the current thumbnail without modification, replaces the stored bytes, and advances `expires_at` by 30 days. Transient API/rate failures reschedule refresh; permanent video or thumbnail unavailability removes the cover and marks its source resource deleted. PostgreSQL claim/locking prevents concurrent workers from processing the same resource, and missing storage files are treated as an already-achieved deletion state.

Only successful imports create `RecipeResource` rows. If the import fails before a `Recipe` exists, full API text and `VideoEvidence` are discarded after processing; bounded diagnostics remain in job events and telemetry. `RecipeResource.recipe_id` remains non-nullable, and no second failed-import resource table is introduced.

### Job events and telemetry

The Gemini stage has job events distinct from the existing OpenAI recipe-extractor events:

```text
VIDEO_EVIDENCE_EXTRACTION_SUCCEEDED
VIDEO_EVIDENCE_EXTRACTION_FAILED
```

`VIDEO_EVIDENCE_EXTRACTION_SUCCEEDED` is emitted for every structurally valid Gemini response. Its payload always includes `confidence`. It also includes provider, model, platform, whether the evidence passed the threshold, an optional rejection reason, latency, and available token usage. A low-confidence response therefore produces a success event with `accepted=false` and `rejectionReason=LOW_CONFIDENCE`, but the evidence body is discarded.

`VIDEO_EVIDENCE_EXTRACTION_FAILED` records provider error classification, model, platform, and latency for API, timeout, video-access, or structured-response failures. Neither event contains the full evidence, description, or credentials. The existing `EXTRACTOR_REQUESTED` and `EXTRACTOR_SUCCEEDED` events continue to describe the later OpenAI recipe extraction stage.

Structured telemetry records:

- YouTube API request count, latency, result/error classification, and rate/quota failures;
- video duration and normalized description length;
- Gemini latency, token usage, confidence, threshold acceptance, and fallback decision;
- whether the OpenAI call was skipped and the normal OpenAI usage/latency data;
- total import duration;
- later, cleanup/refresh claim, success, retry, deletion, and failure counts.

Raw evidence, descriptions, thumbnails, and credentials are not copied into logs or event payloads.

### Delivery sequence

The integration is delivered in independently verifiable milestones:

1. Working YouTube import: URL dispatch, YouTube Data API validation, 15-minute limit, Gemini `VideoEvidence`, confidence/description fallbacks, OpenAI integration, lifecycle fields and expiry assignment, unchanged thumbnail cover with attribution/link behavior, job events, telemetry, and focused tests.
2. Expired-resource cleanup: user-deletion reasons, idempotent cleanup domain service, Dramatiq actor, scheduler, and non-cover cleanup.
3. Cover refresh: periodic unchanged-thumbnail refresh, transient retry, permanent-unavailability cleanup, and lifecycle tests.

The working import may be used by the current private application while the later lifecycle milestones are completed. Public release requires the retention lifecycle and a separate compliance review.

### YouTube-specific test coverage

Backend coverage includes:

- accepted watch, Shorts, and `youtu.be` forms plus rejection through common URL validation;
- canonicalization and video-id parsing without an API request for invalid input;
- public/unavailable/private/unlisted/live/processing/duration boundary responses;
- one-call metadata extraction and deterministic thumbnail selection;
- rate-limit retry, exhausted quota, `Retry-After`, and non-retryable failures;
- Gemini schema validation, empty evidence, provider failure, and confidence immediately below/at the `0.70` boundary;
- description immediately below/at the 200-character boundary;
- fallback with and without other meaningful sources and proof that skipped OpenAI calls do not occur;
- separation of persisted metadata and usable evidence resources;
- proof that low-confidence evidence is not persisted;
- source order and the existing attachments-first capacity invariant;
- proof that thumbnail bytes are unchanged and the thumbnail is absent from both AI requests;
- success/failure event payloads, including mandatory success-event confidence and absence of source content;
- `expires_at`, deletion timestamps/reasons, idempotent cleanup, cover refresh, transient retry, and permanent-unavailability behavior.

### Future improvements and TODO

- Compare the selected two-stage strategy with direct Gemini recipe extraction. Record quality, latency, token usage, failure isolation, source reconciliation, and implementation complexity before considering a mode switch or A/B feature flag.
- Consider a stronger Gemini model only after `gemini-2.5-flash` telemetry identifies a concrete quality problem; do not add an automatic stronger-model fallback in the first version.
- Complete a YouTube API compliance audit and legal/policy review before making the application public. Reconfirm description-derived recipe use, metadata retention, thumbnail presentation, branding, and refresh behavior against the policies current at launch time.
- Revisit the 15-minute, 200-character, and `0.70` defaults using production telemetry rather than model self-confidence alone.

## Testing Strategy

Backend tests:

- Unit tests for validation, source ordering, capacity rules, source status mapping, review flag creation, cover selection, storage cleanup.
- Integration tests for import job lifecycle with fake AI and fake URL loaders.
- API tests with FastAPI test client.
- Migration tests or at least Alembic upgrade smoke test.

Frontend tests:

- Import form behavior.
- Polling state transitions.
- Recipe detail note editing.
- Warning flag display/resolve.

Parity fixtures:

Use cases from the existing MVP testing history:

- only images with full recipe;
- only text with full recipe;
- only URL with full recipe;
- URL plus attachments;
- URL plus text;
- conflicting sources;
- ignored sources;
- low-confidence extraction;
- Instagram carousel over image limit;
- Threads multi-part post;
- video post with transcript;
- video post with poster only;
- duplicate submit using same `clientImportId`.

## Development Commands

Use `uv` for backend:

```bash
cd backend
uv sync
uv run fastapi dev app/main.py
uv run pytest
uv run alembic upgrade head
```

Use frontend package scripts:

```bash
cd frontend
pnpm install
pnpm dev
pnpm test
pnpm typecheck
```

Optional root `Makefile` commands:

```makefile
backend-dev
backend-test
frontend-dev
frontend-test
dev
```

The Makefile is convenience only. Backend and frontend must remain runnable independently.

## Migration Strategy From Current MVP

The current repository is a reference, not a dependency.

Use it for:

- data model comparison;
- import flow behavior;
- prompt and AI schema behavior;
- edge-case tests;
- URL loader behavior;
- cover crop behavior;
- documentation diagrams.

Do not make the new project import TypeScript code or depend on the old app at runtime.

Implementation should start with backend foundations and job lifecycle before porting the full import pipeline. This creates the right async shape early and avoids building a synchronous import API that must later be redesigned.

## Open Decisions

1. Exact new repository remote name and GitHub setup.
2. Whether collections are required in the first parity milestone or can follow after imports and recipe detail are stable.
3. Whether to use generated TypeScript API types from OpenAPI in the first version or write a small manual frontend API client first.
4. Whether local auth remains a fixed default user or we introduce a lightweight client id concept now to prepare for mobile/cloud.
5. Whether the first version needs resource review/delete UI or only source display and warning flags.
