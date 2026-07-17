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

## Recommended Stack

### Backend

- Python 3.12+.
- FastAPI for HTTP API and OpenAPI generation.
- SQLAlchemy 2.x ORM.
- Alembic migrations.
- SQLite for local development.
- Pydantic settings for configuration.
- `uv` and `pyproject.toml` for dependency and script management.
- In-process background worker for local import jobs.
- Local filesystem storage behind a storage interface.

### Frontend

- React + Vite + TypeScript.
- TanStack Query for server-state fetching, caching, mutations, and polling.
- Plain CSS or a small CSS module setup initially; avoid heavy UI frameworks until the workflows stabilize.
- `pnpm` for frontend package management unless we later choose another JS package manager.

TanStack Query is useful here because import status polling and recipe cache invalidation are core workflows. It lets the UI submit an import job, poll `/imports/{jobId}`, refetch recipe lists when the job succeeds, and handle loading/error states without writing custom request lifecycle code everywhere. It is a frontend-only choice and does not couple the backend to React.

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

