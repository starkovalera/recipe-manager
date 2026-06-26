# Recipe Manager Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the greenfield FastAPI + React/Vite rewrite of the recipe MVP while preserving the current import pipeline behavior and keeping backend/frontend separable.

**Architecture:** The backend owns all business logic behind HTTP APIs, SQLite state, local filesystem storage, and provider interfaces for AI, URL loading, video transcription, cover validation, and storage. The frontend is an independent React/Vite app that talks to the backend over HTTP with TanStack Query for mutations, polling, and cache invalidation. Imports are asynchronous: `POST /imports` persists an `ImportJob`, an in-process worker processes it, and the frontend polls `GET /imports/{jobId}` until terminal state. Runtime profiles preserve the old local workflow: `dev` keeps a persistent database and uploaded files, while `preview` wipes its database and upload directory on backend restart.

**Tech Stack:** Python 3.12+, uv, FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings, SQLite, pytest; React, Vite, TypeScript, TanStack Query, Vitest/Testing Library, pnpm.

---

## Approval Gate

Do not write application code until this plan is reviewed and approved.

## Sync-First Pivot

Approved implementation order update:

- First milestone is **working local MVP parity with synchronous import processing**, matching the old `recipe-mvp` behavior more closely.
- Keep the `ImportJob` model and `clientImportId` duplicate guard, but `POST /imports` may execute the full import pipeline synchronously and return a terminal job for the local MVP.
- Build and verify the hard behavior first: mixed sources, attachments-first image capacity, URL loaders, Threads/Instagram, text evidence, video transcript/poster boundary, AI quality rules, source statuses, review flags, cover selection/generation, and cleanup.
- After sync parity is working locally, add the real background queue/worker without changing the frontend-facing import status contract.

This replaces the earlier execution order that tried to establish async worker behavior before porting the full import pipeline.

This plan assumes the first implementation milestone includes:

- Backend scaffold, database, migrations, local storage, default local user/client identity, async import jobs, import pipeline parity, recipe APIs, media serving, and review flags.
- Frontend scaffold, import flow with polling, recipe list, recipe detail/edit, notes, warning flag display/resolve, and source display.
- Collections are included as backend models and minimal list/detail UI only if implementation time remains after import and recipe detail are stable.
- GitHub repository: `https://github.com/starkovalera/recipe-manager`.

## Spec Review

The design is strong enough to implement from, but these points should be explicitly settled before autonomous execution:

1. **Image priority:** Attachments-first is approved and authoritative. Uploaded attachments occupy image capacity before URL images or video posters; URL images use only remaining capacity. Do not port the old remote-first `importCapacity.ts` behavior.
2. **Client identity:** Use a generated/stable local `clientId` plus fixed default user for now. Store the client id in frontend localStorage and send it as `X-Client-Id`. This supports per-client import limits without introducing auth.
3. **Runtime profiles:** Preserve two local runtime setups from the old project. `dev` uses persistent SQLite and persistent uploads; `preview` uses separate SQLite/uploads and clears both on backend startup for debugging and local testing.
4. **Collections:** Treat collections as parity-after-core. Create models/migrations only if cheap, but do not block import/recipe/detail delivery on collection UI.
5. **Frontend API types:** Start with a small manual TypeScript API client. Add OpenAPI generated types later only after endpoints stabilize.
6. **URL loaders:** First parity should include generic URL, Instagram, and Threads loaders because they carry important source-order and capacity behavior. Use fake/network-free tests; live platform behavior is not part of normal CI.
7. **Video:** Implement transcript + poster boundary with fake processor tests. Real OpenAI transcription and ffmpeg integration can be a provider module with graceful unavailable behavior.
8. **Cover guard:** Keep the interface and feature flag, default off. Implement deterministic cover generation/autocrop first; guard provider can be fake-tested and wired to OpenAI later.
9. **Repository remote:** The target repository is `starkovalera/recipe-manager`; local `origin` should point to `https://github.com/starkovalera/recipe-manager.git`.

If any of these assumptions are wrong, update this document before implementation.

## Reference Inputs

Read these old repo files as behavior references only. Do not import or modify the old project.

- `C:\Users\stark\Documents\recipes\docs\import-pipeline-flow.md`
- `C:\Users\stark\Documents\recipes\docs\import-pipeline-notes.md`
- `C:\Users\stark\Documents\recipes\src\server\imports\importService.ts`
- `C:\Users\stark\Documents\recipes\src\server\ai\types.ts`
- `C:\Users\stark\Documents\recipes\src\server\ai\recipeExtractionPrompt.ts`
- `C:\Users\stark\Documents\recipes\src\server\imports\urlLoaders\*.ts`
- `C:\Users\stark\Documents\recipes\prisma\schema.prisma`
- `C:\Users\stark\Documents\recipes\src\server\imports\*.test.ts`
- `C:\Users\stark\Documents\recipes\src\server\ai\*.test.ts`

Important reference behavior to preserve:

- Attachments are saved/accepted first and occupy image capacity before URL images or video posters.
- URL images use only remaining `MAX_IMPORT_IMAGES` capacity.
- Text input is evidence and does not count against image capacity.
- Video contributes transcript text and poster image only; no frame slicing.
- Failed video processing should not fail an import if non-video evidence remains usable.
- AI returns `recipe`, `quality`, and optional `coverCandidate`.
- `quality.confidence <= IMPORT_MIN_CONFIDENCE` fails import.
- `quality.hasConflicts || quality.hasIgnored || quality.confidence <= IMPORT_WARN_CONFIDENCE` creates an open review flag.
- `primarySourceRefs` and `ignoredSourceRefs` drive recipe source statuses.
- Single URL import normalizes internal conflicts by clearing `hasConflicts`, `hasIgnored`, and `ignoredSourceRefs`.
- Cover candidate must reference an accepted image source before cover generation.
- Cover guard remains feature-flagged and off by default.
- Cleanup deletes files saved for failed imports and never deletes outside configured storage root.
- Local runtime behavior has separate `dev` and `preview` profiles: `dev` is persistent; `preview` wipes database and uploaded files on restart.

## Runtime Profiles

Implement profile selection in backend settings with `APP_ENV`, default `dev`.

- `APP_ENV=dev`
  - `DATABASE_URL` defaults to `sqlite:///./storage/dev/app.db`.
  - `UPLOAD_DIR` defaults to `./storage/dev/uploads`.
  - Startup creates directories and runs against existing data.
  - Never clears database or uploaded files automatically.
- `APP_ENV=preview`
  - `DATABASE_URL` defaults to `sqlite:///./storage/preview/app.db`.
  - `UPLOAD_DIR` defaults to `./storage/preview/uploads`.
  - Startup clears the preview SQLite file and preview upload directory before migrations/default user initialization.
  - Cleanup must be guarded so only paths under `backend/storage/preview/` are deleted.
- `APP_ENV=test`
  - Tests should use temporary database and storage paths where possible.
  - Tests must not touch dev or preview storage.

Add explicit scripts or documented commands for both modes:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv run fastapi dev app/main.py
```

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
$env:APP_ENV="preview"; uv run fastapi dev app/main.py
```

## Target File Map

### Root

- Create `README.md`: local setup, backend/frontend commands, `dev`/`preview` runtime commands, env examples.
- Create `.gitignore`: Python, Node, SQLite, storage, coverage artifacts.
- Create `Makefile`: convenience commands only.
- Keep `docs/design.md`.
- Create/maintain `docs/api.md`: human-readable API contract.
- Create/maintain `docs/import-pipeline.md`: final Python import flow notes.

### Backend

- Create `backend/pyproject.toml`: uv project, runtime dependencies, pytest/ruff/mypy optional tooling.
- Create `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/*.py`.
- Create `backend/app/main.py`: FastAPI app factory, routers, lifespan worker startup.
- Create `backend/app/core/config.py`: Pydantic settings.
- Create `backend/app/core/runtime.py`: runtime profile startup behavior, including preview cleanup guard.
- Create `backend/app/core/errors.py`: app error codes and HTTP mapping.
- Create `backend/app/core/ids.py`: UUID helpers.
- Create `backend/app/core/security.py`: request client id/default user helpers.
- Create `backend/app/db/base.py`, `backend/app/db/session.py`, `backend/app/db/init.py`.
- Create `backend/app/models/*.py`: SQLAlchemy entities and enums.
- Create `backend/app/schemas/*.py`: Pydantic request/response models.
- Create `backend/app/api/routes/*.py`: health, recipes, imports, media, review flags, sources.
- Create `backend/app/services/recipes.py`: recipe CRUD/editing and serialization.
- Create `backend/app/services/review_flags.py`: resolve/unresolve behavior.
- Create `backend/app/storage/base.py`, `backend/app/storage/local.py`: storage interface and local implementation.
- Create `backend/app/media/images.py`: image validation, data URL encoding, cover generation/autocrop.
- Create `backend/app/imports/jobs.py`: job creation, duplicate handling, active-limit checks, stale job failure.
- Create `backend/app/imports/worker.py`: in-process queue, job claiming, retry/requeue on startup.
- Create `backend/app/imports/pipeline.py`: orchestration of validation, source loading, AI extraction, DB writes, cleanup.
- Create `backend/app/imports/sources.py`: ready source types, source refs, status mapping.
- Create `backend/app/imports/url_loaders/*.py`: generic, Instagram, Threads, registry, remote fetch guard.
- Create `backend/app/imports/video/*.py`: video processor interface, poster/transcript handling.
- Create `backend/app/ai/schemas.py`: extraction response schema.
- Create `backend/app/ai/prompt.py`: ported extraction prompt.
- Create `backend/app/ai/provider.py`: provider protocol and factory.
- Create `backend/app/ai/openai_provider.py`: OpenAI implementation.
- Create `backend/app/ai/fake_provider.py`: deterministic fake provider for tests/dev.
- Create `backend/tests/**`: focused unit/API/integration tests.

### Frontend

- Create `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig*.json`, `frontend/index.html`.
- Create `frontend/src/main.tsx`, `frontend/src/app/App.tsx`, `frontend/src/app/queryClient.ts`.
- Create `frontend/src/api/client.ts`: manual HTTP client.
- Create `frontend/src/api/types.ts`: frontend API response/request types.
- Create `frontend/src/api/clientId.ts`: stable local client id.
- Create `frontend/src/pages/RecipeListPage.tsx`.
- Create `frontend/src/pages/ImportPage.tsx`.
- Create `frontend/src/pages/RecipeDetailPage.tsx`.
- Create `frontend/src/pages/CollectionsPage.tsx` only if collections are included in first milestone.
- Create `frontend/src/components/import/*`: source form, job status, error display.
- Create `frontend/src/components/recipes/*`: list item, editor, ingredients/instructions, media, sources, review flags.
- Create `frontend/src/styles/*.css`: app layout and component styling.
- Create `frontend/src/**/*.test.tsx`: import polling and recipe editing tests.

## Commands

Use these commands as verification gates during implementation.

Backend:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv sync
uv run pytest
uv run alembic upgrade head
uv run python -m compileall app tests
```

Frontend:

```powershell
cd C:\Users\stark\Documents\recipe-manager\frontend
pnpm install
pnpm test
pnpm typecheck
pnpm build
```

Full local smoke:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv run fastapi dev app/main.py
```

```powershell
cd C:\Users\stark\Documents\recipe-manager\frontend
pnpm dev
```

## Task 1: Repository Scaffold and Tooling

**Files:**

- Create root files: `.gitignore`, `README.md`, `Makefile`
- Create backend scaffold under `backend/`
- Create frontend scaffold under `frontend/`
- Modify docs only if setup commands need clarification

- [ ] Create `backend/pyproject.toml` with FastAPI, uvicorn/fastapi dev support, SQLAlchemy, Alembic, Pydantic Settings, python-multipart, httpx, Pillow, OpenAI SDK, pytest, pytest-asyncio.
- [ ] Create importable `backend/app` package with empty app factory in `backend/app/main.py`.
- [ ] Create `GET /health` returning `{"status":"ok"}`.
- [ ] Add backend pytest config and `backend/tests/api/test_health.py`.
- [ ] Run `uv sync` and `uv run pytest backend/tests/api/test_health.py -q`; expected pass.
- [ ] Add README commands for backend `dev` and `preview` startup, with `preview` clearly marked as destructive to preview-only storage.
- [ ] Create frontend Vite React TypeScript app files manually or through package tooling.
- [ ] Add a minimal app shell that renders recipe manager navigation without calling backend yet.
- [ ] Add Vitest config and a smoke render test.
- [ ] Run `pnpm test`, `pnpm typecheck`, and `pnpm build`; expected pass.
- [ ] Commit: `chore: scaffold backend and frontend`

## Task 2: Backend Configuration, Database, and Migrations

**Files:**

- Create `backend/app/core/config.py`
- Create `backend/app/core/runtime.py`
- Create `backend/app/db/session.py`, `backend/app/db/base.py`, `backend/app/db/init.py`
- Create `backend/app/models/*.py`
- Create `backend/alembic/*`
- Test `backend/tests/db/test_migrations.py`
- Test `backend/tests/core/test_runtime_profiles.py`

- [ ] Define settings with defaults from `docs/design.md`: `APP_ENV`, database URL, upload dir, import limits, OpenAI model names, cover guard flag, ffmpeg paths, stale job timeout.
- [ ] Implement `APP_ENV=dev` defaults to persistent `backend/storage/dev/app.db` and `backend/storage/dev/uploads`.
- [ ] Implement `APP_ENV=preview` defaults to isolated `backend/storage/preview/app.db` and `backend/storage/preview/uploads`.
- [ ] Implement `APP_ENV=test` defaults for tests that never touch dev or preview data.
- [ ] Implement preview startup cleanup that deletes only the configured preview database file and files under the configured preview upload directory after resolving absolute paths under `backend/storage/preview`.
- [ ] Refuse preview cleanup if resolved paths are outside the preview storage root.
- [ ] Define SQLAlchemy enums equivalent to the old Prisma enums: source name/type/status, import job status/source status, image role, cover source, review flag status/type.
- [ ] Define UUID primary keys as strings or SQLAlchemy UUID-compatible values for SQLite portability.
- [ ] Implement models for user, recipe, ingredient, tag, recipe tag, recipe image, recipe source, review flag, import job, import job source, collection, recipe collection.
- [ ] Add unique constraints: user email, owner/name for tags and collections, owner/clientImportId for import jobs, recipe image id/recipe id where source references need scoped integrity.
- [ ] Add Alembic initial migration.
- [ ] Add `ensure_default_user(session)` that creates a fixed local user if absent.
- [ ] Test migration upgrade on a temp SQLite DB.
- [ ] Test dev profile does not remove existing DB/upload files.
- [ ] Test preview profile removes only preview DB/upload files and refuses unsafe paths.
- [ ] Test model relationships by creating a recipe with ingredients, image, source, review flag, and import job.
- [ ] Run `uv run alembic upgrade head` and `uv run pytest backend/tests/db backend/tests/core -q`; expected pass.
- [ ] Commit: `feat: add backend data model`

## Task 3: Storage and Media Foundations

**Files:**

- Create `backend/app/storage/base.py`
- Create `backend/app/storage/local.py`
- Create `backend/app/media/images.py`
- Create `backend/app/api/routes/media.py`
- Tests under `backend/tests/storage/` and `backend/tests/media/`

- [ ] Define `StorageService` protocol with `save`, `read`, `delete`, `open_path` or equivalent for local media serving.
- [ ] Implement `LocalStorageService` that stores files under configured `UPLOAD_DIR` using generated storage keys and respects the active runtime profile path.
- [ ] Guard deletes by resolving paths and confirming they remain under storage root.
- [ ] Implement image MIME validation for JPEG/PNG/WebP initially.
- [ ] Implement bytes-to-data-url helper for AI image input.
- [ ] Implement deterministic cover generation: load selected image, apply normalized crop if present, otherwise autocrop/full-image fit, save generated cover.
- [ ] Add `GET /media/{storage_key:path}` that serves local files through FastAPI.
- [ ] Test save/read/delete and path traversal rejection.
- [ ] Test dev and preview storage roots are separate.
- [ ] Test cover generation creates a separate storage key and does not mutate source image.
- [ ] Run `uv run pytest backend/tests/storage backend/tests/media -q`; expected pass.
- [ ] Commit: `feat: add local storage and media service`

## Task 4: API Error Contract and Client Identity

**Files:**

- Create `backend/app/core/errors.py`
- Create `backend/app/core/security.py`
- Modify `backend/app/main.py`
- Tests under `backend/tests/api/test_errors.py`

- [ ] Define stable error codes matching old behavior where applicable: `INVALID_URL`, `TEXT_TOO_LONG`, `NOT_A_RECIPE`, `TOO_MANY_FILES`, `INVALID_FILE_TYPE`, `FILE_TOO_LARGE`, `ACTIVE_IMPORT_EXISTS`, `AI_UNAVAILABLE`, `INVALID_EXTRACTION_RESULT`, `MIXED_SOURCE_PLATFORMS`, `IMPORT_NOT_FOUND`.
- [ ] Define API error response shape: `{"errorCode": "...", "message": "..."}`.
- [ ] Implement request client id extraction from `X-Client-Id`, normalized to max 128 chars.
- [ ] Use fixed default user for local mode.
- [ ] Add tests for invalid/missing client id fallback, error serialization, and HTTP status mapping.
- [ ] Run `uv run pytest backend/tests/api/test_errors.py -q`; expected pass.
- [ ] Commit: `feat: add api error contract`

## Task 5: Recipe CRUD, Notes, Sources, and Review Flags

**Files:**

- Create `backend/app/schemas/recipes.py`
- Create `backend/app/services/recipes.py`
- Create `backend/app/services/review_flags.py`
- Create `backend/app/api/routes/recipes.py`
- Create `backend/app/api/routes/review_flags.py`
- Tests under `backend/tests/api/test_recipes.py`, `backend/tests/services/test_recipes.py`

- [ ] Implement `GET /recipes` with simple list sorted by newest first.
- [ ] Implement `GET /recipes/{recipe_id}` returning ingredients, tags, images/media URLs, sources, and open/resolved review flags.
- [ ] Implement `PATCH /recipes/{recipe_id}` for title, servings, cook time, instructions, ingredients, tags, and note.
- [ ] Trim and truncate note to `MAX_RECIPE_NOTE_CHARS`; never send note through import AI.
- [ ] Implement `DELETE /recipes/{recipe_id}` with DB cascade. Physical media deletion can be deferred to a later cleanup task unless tests prove it is necessary now.
- [ ] Implement `GET /recipes/{recipe_id}/sources`.
- [ ] Implement `PATCH /recipes/{recipe_id}/review-flags/{flag_id}` to resolve/unresolve with `resolvedAt`.
- [ ] Add API tests for list/detail/update/delete, note truncation, source display, and review flag resolve.
- [ ] Run `uv run pytest backend/tests/api/test_recipes.py backend/tests/services/test_recipes.py -q`; expected pass.
- [ ] Commit: `feat: add recipe api`

## Task 6: AI Boundary and Extraction Schema

**Files:**

- Create `backend/app/ai/schemas.py`
- Create `backend/app/ai/prompt.py`
- Create `backend/app/ai/provider.py`
- Create `backend/app/ai/fake_provider.py`
- Create `backend/app/ai/openai_provider.py`
- Tests under `backend/tests/ai/`

- [ ] Port the extraction schema: title, ingredients, instructions, servings, cook time, nutrition estimate, author name, tags, nullable quality, nullable cover candidate.
- [ ] Require recipe results to include `quality`; normalize missing optional fields to safe defaults only where old schema did.
- [ ] Port the prompt text and preserve the source-injection warning.
- [ ] Define provider protocols: `RecipeExtractionProvider.extract`, `CoverValidationProvider.validate`, `VideoTranscriptionProvider.transcribe`.
- [ ] Implement fake provider with deterministic recipe output for image/url/text evidence and `NOT_A_RECIPE` for empty/irrelevant evidence.
- [ ] Implement OpenAI provider behind the interface with strict JSON parsing and schema validation.
- [ ] Add tests for schema validation, prompt/source label construction, invalid AI JSON failure, fake provider behavior, and cover validation interface.
- [ ] Run `uv run pytest backend/tests/ai -q`; expected pass.
- [ ] Commit: `feat: add ai extraction boundary`

## Task 7: Import Source Types and Capacity Rules

**Files:**

- Create `backend/app/imports/sources.py`
- Create `backend/app/imports/validation.py`
- Tests under `backend/tests/imports/test_sources.py`, `backend/tests/imports/test_validation.py`

- [ ] Define ready source dataclasses/Pydantic models for `IMAGE`, `URL`, and `TEXT`.
- [ ] Define stable source refs: image refs keep generated source ref; URL refs are `url:{position}`; text refs are `text:{position}`.
- [ ] Implement source id normalization so AI may return either raw image source ref or `image:{sourceRef}`.
- [ ] Implement attachment-first capacity: accepted attachment count is all valid attachments up to `MAX_IMPORT_IMAGES`; remaining URL image capacity is `MAX_IMPORT_IMAGES - accepted_attachments`.
- [ ] Fail synchronously if uploaded attachment count exceeds `MAX_IMPORT_IMAGES`.
- [ ] Implement source assessment mapping: primary refs -> `used`, ignored refs -> `ignored`, otherwise `unknown`.
- [ ] Implement single URL quality normalization.
- [ ] Implement review flag decision from quality thresholds.
- [ ] Add tests ported from old cases: too many files, text too long, source refs, ignored source status, low-confidence warning, confidence equal to min fails, single URL conflict normalization, attachments-first capacity.
- [ ] Run `uv run pytest backend/tests/imports/test_sources.py backend/tests/imports/test_validation.py -q`; expected pass.
- [ ] Commit: `feat: add import source rules`

## Task 8: URL Loader Registry and Remote Fetch Guard

**Files:**

- Create `backend/app/imports/url_loaders/types.py`
- Create `backend/app/imports/url_loaders/remote_fetch.py`
- Create `backend/app/imports/url_loaders/generic.py`
- Create `backend/app/imports/url_loaders/instagram.py`
- Create `backend/app/imports/url_loaders/threads.py`
- Create `backend/app/imports/url_loaders/registry.py`
- Tests under `backend/tests/imports/url_loaders/`

- [ ] Define loader interface: `supports(url)`, `inspect(url, options)`, `load(url, options)`.
- [ ] Implement normalized HTTP/HTTPS URL validation and rejection of non-HTTP schemes.
- [ ] Implement loader ordering: Instagram, Threads, generic fallback.
- [ ] Implement remote fetch helper with redirect cap, byte limit, content-length precheck, and private/non-public IP rejection where resolvable.
- [ ] Implement generic loader for metadata description, page text, and preview image, with `max_images=0` short-circuit.
- [ ] Implement Instagram loader behavior: inspect full non-video photo count, skip videos as images, load largest photo candidates in carousel order, preserve positions, expose video metadata/poster URL when present.
- [ ] Implement Threads loader behavior: support `threads.net` and `threads.com`, include requested primary chain by same author, skip unrelated replies/related posts, expose video metadata/poster URL.
- [ ] Test registry dispatch, URL normalization, byte limits, max images zero, Instagram full carousel count, Threads primary chain behavior, and video metadata.
- [ ] Run `uv run pytest backend/tests/imports/url_loaders -q`; expected pass.
- [ ] Commit: `feat: add url loaders`

## Task 9: Video Processor Boundary

**Files:**

- Create `backend/app/imports/video/processor.py`
- Create `backend/app/imports/video/openai_transcriber.py`
- Tests under `backend/tests/imports/video/`

- [ ] Define video processor input from URL loader video metadata: URL, poster URL, original name, position.
- [ ] Implement fake video processor returning optional transcript and optional poster image bytes.
- [ ] Implement real processor skeleton that can download poster and transcribe audio when configured, but returns recoverable failure when dependencies are missing.
- [ ] Ensure video poster consumes remaining image capacity and transcript does not.
- [ ] Ensure video failure is logged and non-video import sources continue.
- [ ] Test transcript-only, poster-only, poster skipped when attachments fill capacity, processing failure continues, and no frame slicing retry.
- [ ] Run `uv run pytest backend/tests/imports/video -q`; expected pass.
- [ ] Commit: `feat: add video import boundary`

## Task 10: Import Job Lifecycle API (Sync-First)

**Files:**

- Create `backend/app/schemas/imports.py`
- Create `backend/app/imports/jobs.py`
- Create `backend/app/imports/worker.py`
- Create `backend/app/api/routes/imports.py`
- Modify `backend/app/main.py`
- Tests under `backend/tests/imports/test_jobs.py`, `backend/tests/api/test_imports_jobs.py`

- [ ] Implement `POST /imports` accepting multipart `url`, `text`, files, and required `clientImportId`.
- [ ] Synchronously validate at least one source, text limit, URL format, file count/type/size.
- [ ] Implement duplicate handling: same `clientImportId` and succeeded returns existing job/recipe; same id active returns existing active job or `ACTIVE_IMPORT_EXISTS` consistently; failed duplicate may create a new job only if client creates a new `clientImportId`.
- [ ] Enforce `MAX_PARALLEL_IMPORTS_PER_CLIENT` for `pending` or `processing` jobs.
- [ ] Persist `ImportJob(status=pending)` and `ImportJobSource` rows before returning.
- [ ] Implement `GET /imports/{job_id}` with status, timestamps, error, and created recipe id.
- [ ] For the sync-first MVP, `POST /imports` creates `ImportJob`, executes the import pipeline immediately, and returns a terminal `succeeded` or `failed` job.
- [ ] Preserve `clientImportId` duplicate handling: same succeeded import returns the existing job/recipe; same active import returns existing active job or `ACTIVE_IMPORT_EXISTS` consistently.
- [ ] Keep status polling endpoint so the frontend contract already matches the later async worker version.
- [ ] Defer real worker startup, queue claiming, and stale active job failure to the post-parity async phase.
- [ ] Add tests for immediate terminal response, polling payload, duplicate submit, active limit behavior, and failure persistence.
- [ ] Run `uv run pytest backend/tests/imports/test_jobs.py backend/tests/api/test_imports_jobs.py -q`; expected pass.
- [ ] Commit: `feat: add async import jobs`

## Task 11: Import Pipeline Orchestration

**Files:**

- Create `backend/app/imports/pipeline.py`
- Modify `backend/app/imports/jobs.py`
- Modify `backend/app/imports/sources.py`
- Tests under `backend/tests/imports/test_pipeline.py`

- [ ] Implement pipeline input from persisted job and request payload metadata.
- [ ] Save uploaded attachments first, create ready image sources, and add saved files to cleanup tracking.
- [ ] Add user text as ready text source when present.
- [ ] Inspect/load URL with `max_images` equal to remaining image capacity and `max_videos=MAX_IMPORT_VIDEOS`.
- [ ] Add URL caption/body text as URL evidence.
- [ ] Save accepted URL images in loader order and preserve source positions.
- [ ] Process URL videos: add transcript as text evidence; save poster only while image capacity remains.
- [ ] If accepted evidence is empty after partial failures, fail as `NOT_A_RECIPE`.
- [ ] Call recipe extraction provider with structured ready sources.
- [ ] On provider exception or AI unavailable, fail job and cleanup saved files.
- [ ] Validate extracted recipe and normalize source ids.
- [ ] Apply single URL quality normalization before confidence/review decisions.
- [ ] Fail and cleanup when confidence is `<= IMPORT_MIN_CONFIDENCE`.
- [ ] Select cover from AI candidate only if candidate references accepted image source.
- [ ] If cover guard is enabled, validate candidate; if rejected, use configured fallback candidates or no cover.
- [ ] Generate cover image from selected source and add to cleanup tracking until DB transaction succeeds.
- [ ] In one DB transaction create recipe, ingredients, tags, source images, cover image, recipe sources, review flag, and mark job succeeded.
- [ ] On any failure before recipe creation, cleanup saved files and mark job failed with stable error code/message.
- [ ] Test parity cases: only images, only text, only URL, URL plus attachments, URL plus text, ignored sources, conflicting sources, low confidence, video transcript/poster, cover candidate, cover guard disabled, cleanup on failure.
- [ ] Run `uv run pytest backend/tests/imports/test_pipeline.py -q`; expected pass.
- [ ] Commit: `feat: implement import pipeline`

## Task 12: Backend Integration and Documentation

**Files:**

- Modify `docs/api.md`
- Modify `docs/import-pipeline.md`
- Add `backend/tests/api/test_imports_integration.py`

- [ ] Add integration tests using fake AI, fake URL loader, fake video processor, and local temp storage through FastAPI test client.
- [ ] Verify import job succeeds end-to-end and recipe detail returns created recipe, media URLs, sources, and review flags.
- [ ] Verify failed import returns terminal failed status and does not leave saved files in temp storage.
- [ ] Verify OpenAPI schema includes all planned routes.
- [ ] Write `docs/api.md` with endpoint list, request/response shapes, error codes, and polling behavior.
- [ ] Write `docs/import-pipeline.md` with final Python source ordering, capacity, quality, cover, video, cleanup rules, and `dev`/`preview` storage separation.
- [ ] Run full backend verification: `uv run pytest`, `uv run alembic upgrade head`, `uv run python -m compileall app tests`.
- [ ] Commit: `test: add backend import integration coverage`

## Task 13: Frontend API Client and App Shell

**Files:**

- Create `frontend/src/api/client.ts`
- Create `frontend/src/api/types.ts`
- Create `frontend/src/api/clientId.ts`
- Create `frontend/src/app/queryClient.ts`
- Create `frontend/src/app/App.tsx`
- Tests under `frontend/src/api/*.test.ts`

- [ ] Implement API base URL from `VITE_API_BASE_URL`, default `http://localhost:8000`.
- [ ] Implement stable local `clientId` in localStorage and include it as `X-Client-Id`.
- [ ] Implement typed client functions: list recipes, get recipe, patch recipe, delete recipe, create import, get import job, resolve review flag.
- [ ] Implement API error parsing into a frontend error type with `errorCode` and `message`.
- [ ] Set up TanStack Query provider and simple route state. Use React Router only if installed intentionally; otherwise keep a small local router for MVP.
- [ ] Add tests for client id persistence, API error parsing, and multipart import request construction.
- [ ] Run `pnpm test` and `pnpm typecheck`; expected pass.
- [ ] Commit: `feat: add frontend api client`

## Task 14: Import Page with Polling

**Files:**

- Create `frontend/src/pages/ImportPage.tsx`
- Create `frontend/src/components/import/ImportForm.tsx`
- Create `frontend/src/components/import/ImportJobStatus.tsx`
- Create `frontend/src/components/import/ImportError.tsx`
- Tests under `frontend/src/pages/ImportPage.test.tsx`

- [ ] Build form with URL input, text textarea, image file input, and submit button.
- [ ] Generate a new `clientImportId` per submit attempt.
- [ ] Disable submit while the `POST /imports` mutation is starting.
- [ ] After successful submit, poll job status every 1-2 seconds with TanStack Query until `succeeded` or `failed`.
- [ ] On succeeded, invalidate recipe list query and show/navigate to recipe detail link.
- [ ] On failed, show backend error code/message visibly.
- [ ] Keep form state intact on failed import so the user can adjust and submit again with a new `clientImportId`.
- [ ] Add tests for submit, polling transition to success, polling transition to failure, duplicate click prevention, and error rendering.
- [ ] Run `pnpm test` and `pnpm typecheck`; expected pass.
- [ ] Commit: `feat: add import polling ui`

## Task 15: Recipe List and Detail/Edit UI

**Files:**

- Create `frontend/src/pages/RecipeListPage.tsx`
- Create `frontend/src/pages/RecipeDetailPage.tsx`
- Create `frontend/src/components/recipes/RecipeListItem.tsx`
- Create `frontend/src/components/recipes/RecipeEditor.tsx`
- Create `frontend/src/components/recipes/RecipeMedia.tsx`
- Create `frontend/src/components/recipes/RecipeSources.tsx`
- Create `frontend/src/components/recipes/ReviewFlags.tsx`
- Tests under `frontend/src/pages/RecipeDetailPage.test.tsx`

- [ ] Render recipe list with title, cover image/default placeholder, tags, and updated timestamp.
- [ ] Render recipe detail with title, ingredients, instructions, note, tags, cover/media, sources, and review flags.
- [ ] Implement editing for title, servings, cook time, ingredients, instructions, tags, and note via `PATCH /recipes/{recipeId}`.
- [ ] Invalidate recipe list/detail queries after edits.
- [ ] Display source statuses `used`, `ignored`, `unknown`; show assessment reason/confidence where available.
- [ ] Display warning/review flags and implement resolve/unresolve mutation.
- [ ] Add tests for loading state, edit save, note save, warning flag resolve, and source status display.
- [ ] Run `pnpm test`, `pnpm typecheck`, `pnpm build`; expected pass.
- [ ] Commit: `feat: add recipe views`

## Task 16: Collections Minimal Parity

**Files:**

- Backend: collection models already created in Task 2; add APIs only if included.
- Frontend: `frontend/src/pages/CollectionsPage.tsx`
- Tests under backend/frontend collection test files

- [ ] If approved as first-milestone scope, add collection list/create/update/delete endpoints and membership update endpoint.
- [ ] Add minimal collections page showing collections and their recipes.
- [ ] If deferred, document deferral in `docs/design.md` or `docs/import-pipeline.md` and keep models unused until later.
- [ ] Run relevant backend and frontend tests.
- [ ] Commit either `feat: add collections api` or `docs: defer collections ui`.

## Task 17: End-to-End Local Smoke and Polish

**Files:**

- Modify `README.md`
- Modify CSS under `frontend/src/styles/`
- Add optional smoke test notes under `docs/`

- [ ] Run full backend verification.
- [ ] Run full frontend verification.
- [ ] Start backend dev server in `APP_ENV=dev` and verify existing dev data persists after restart.
- [ ] Start backend dev server in `APP_ENV=preview` and verify preview database/uploads are cleared after restart while dev data remains untouched.
- [ ] Start frontend dev server against the selected backend.
- [ ] Manually smoke: create import from text only with fake provider, poll to success, open recipe detail, edit note, resolve warning flag if present.
- [ ] Manually smoke: import URL plus attachments with fake loader/provider if test-only route or fixture mode exists; confirm attachments occupy capacity before URL images.
- [ ] Check frontend at desktop and mobile widths for text overflow and obvious layout issues.
- [ ] Update README with exact local commands, environment variables, `dev`/`preview` behavior, storage paths, and known limitations.
- [ ] Commit: `docs: document local development workflow`

## Final Verification Gate

Before claiming the rewrite milestone is complete, run:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv run pytest
uv run alembic upgrade head
uv run python -m compileall app tests
```

```powershell
cd C:\Users\stark\Documents\recipe-manager\frontend
pnpm test
pnpm typecheck
pnpm build
```

Then report:

- Backend test count and pass/fail status.
- Frontend test/build/typecheck status.
- Manual smoke cases completed.
- Any intentionally deferred scope, especially async queue/worker conversion, collections, OpenAPI-generated frontend types, real cloud storage, real auth, live social platform loader verification, video frame slicing, and cover guard-on behavior.

## Risk Register

- **Old capacity helper drift:** Do not port `importCapacity.ts` blindly; it is remote-first. The rewrite must be attachments-first.
- **Preview cleanup safety:** Preview startup is intentionally destructive only inside `backend/storage/preview`. Resolve and verify paths before deleting; never let preview cleanup touch dev storage.
- **SQLite background worker concurrency:** In-process queue is acceptable locally, but job claiming must be DB-backed so polling is reliable after reloads.
- **Social platform fragility:** Keep loaders isolated and heavily fixture-tested. Do not rely on live Instagram/Threads in normal tests.
- **SSRF limits:** Implement best-effort URL validation, DNS checks, redirect checks, and byte caps. Document residual DNS rebinding risk if the final HTTP client resolves independently after prevalidation.
- **Provider coupling:** AI, cover validation, video transcription, URL loading, and storage must stay behind interfaces so local/cloud/mobile evolution does not rewrite UI or domain logic.
- **Cleanup safety:** Every cleanup path must resolve storage keys under the configured storage root before deleting.
- **OpenAPI/type drift:** Manual frontend types can drift. Keep endpoint tests and `docs/api.md` updated; consider generated types after API stabilizes.

