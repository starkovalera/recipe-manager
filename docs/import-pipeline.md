# Current Import Pipeline

This documents the current implementation state after the first backend/frontend vertical slice. It is intentionally narrower than the target design in `docs/design.md`.

```mermaid
flowchart TD
  start["Frontend import form"] --> submit["POST /imports multipart form<br/>clientImportId + optional text/url"]
  submit --> validate{"Synchronous validation"}
  validate -->|"no text and no url"| failNoSource["400 NOT_A_RECIPE"]
  validate -->|"ok"| dedupe{"Existing owner/clientImportId?"}
  dedupe -->|"yes"| returnExisting["Return existing ImportJob"]
  dedupe -->|"no"| createJob["Create ImportJob pending<br/>Create ImportJobSource rows"]
  createJob --> process["Process current job immediately<br/>first vertical slice"]
  process --> ready["Build ReadySource list<br/>TEXT and URL evidence"]
  ready --> fakeAi["FakeRecipeExtractionProvider.extract"]
  fakeAi -->|"not recipe"| failJob["Mark job failed<br/>errorCode NOT_A_RECIPE"]
  fakeAi -->|"recipe result"| statusMap["Map primarySourceRefs / ignoredSourceRefs<br/>to RecipeSource statuses"]
  statusMap --> coverGuard["Cover guard module exists as black box<br/>not invoked by current minimal pipeline"]
  coverGuard --> db["DB transaction-style write<br/>Recipe, Ingredient, RecipeSource"]
  db --> maybeFlag{"hasConflicts OR hasIgnored OR<br/>confidence <= IMPORT_WARN_CONFIDENCE?"}
  maybeFlag -->|"yes"| flag["Create CONTENT_WARNING flag"]
  maybeFlag -->|"no"| success
  flag --> success["Mark ImportJob succeeded<br/>createdRecipeId set"]
  success --> poll["Frontend polls GET /imports/{jobId}"]
  failJob --> poll
  poll --> detail["Frontend can fetch recipe detail"]

  classDef ai fill:#fff0b3,stroke:#b7791f,color:#111,stroke-width:2px;
  classDef fail fill:#ffe0e0,stroke:#b91c1c,color:#111;
  classDef db fill:#e7f5ff,stroke:#1d4ed8,color:#111;
  classDef decision fill:#f3f4f6,stroke:#555,color:#111;

  class fakeAi ai;
  class failNoSource,failJob fail;
  class db,success db;
  class validate,dedupe,maybeFlag decision;
```

## Implemented Rules

- `clientImportId` deduplicates imports for the default local user.
- Text input participates as recipe evidence.
- URL input currently participates as URL evidence without platform loading.
- Fake AI provider returns recipe quality and primary source refs.
- Recipe source statuses are derived from `primarySourceRefs` and `ignoredSourceRefs`.
- Warning flags are created when `quality.hasConflicts`, `quality.hasIgnored`, or `quality.confidence <= IMPORT_WARN_CONFIDENCE`.
- Cover guard logic is isolated in `backend/app/imports/cover_guard.py` so it can be removed from the scenario without changing source rules or API routes.

## Target Gaps Still To Implement

- Real background queue/worker instead of immediate first-slice processing.
- Attachments-first image capacity in the multipart route.
- URL loaders for generic pages, Instagram, and Threads.
- Video transcript and poster image handling.
- Strict AI JSON/OpenAI provider integration.
- Cover generation and optional guard invocation from the pipeline.
- Storage cleanup on failed imports after files are accepted.
