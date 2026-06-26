# Current Import Pipeline

This is the current sync-first implementation state. The API keeps the `ImportJob`
contract so the frontend shape can stay stable when the real background queue is
added later.

```mermaid
flowchart TD
  start["Frontend import form"] --> submit["POST /imports multipart<br/>clientImportId + optional url/text/files"]
  submit --> validate{"Validate request"}
  validate -->|"no usable source"| fail400["400 NOT_A_RECIPE"]
  validate -->|"text too long"| failText["400 TEXT_TOO_LONG"]
  validate -->|"too many/invalid files"| failFiles["400 TOO_MANY_FILES / INVALID_FILE_TYPE / FILE_TOO_LARGE"]
  validate -->|"ok"| dedupe{"Existing owner/clientImportId?"}
  dedupe -->|"yes"| existing["Return existing ImportJob"]
  dedupe -->|"no"| persist["Persist ImportJob pending<br/>Persist TEXT/IMAGE/URL ImportJobSource rows"]

  persist --> process["Process synchronously in POST /imports"]
  process --> tree["Build RecipeSource tree<br/>primary sources have parent_source_id = null"]
  tree --> images["Save attachment images first<br/>IMAGE + source=MANUAL"]
  images --> text["Add text input<br/>TEXT + source=MANUAL"]
  text --> url{"URL source?"}
  url -->|"no"| ai
  url -->|"yes"| remaining["remaining images = MAX_IMPORT_IMAGES - accepted attachments"]
  remaining --> loader["Loader registry<br/>Instagram -> Threads -> Generic"]
  loader --> loadedUrl["Create URL primary row<br/>URL + source=MANUAL"]
  loadedUrl --> children["Create final URL children<br/>TEXT/IMAGE + source=URL<br/>transcript/poster + source=URL_VIDEO"]
  children --> ai["RecipeExtractionProvider.extract<br/>final sources only, type != URL"]

  ai -->|"not recipe"| failJob["Mark ImportJob failed<br/>cleanup saved files"]
  ai --> quality{"confidence <= IMPORT_MIN_CONFIDENCE?"}
  quality -->|"yes"| lowConfidence["Mark ImportJob failed<br/>cleanup saved files"]
  quality -->|"no"| singleUrl["Normalize single URL internal conflicts"]
  singleUrl --> sources["Map primarySourceRefs / ignoredSourceRefs<br/>to final RecipeSource statuses"]
  sources --> cover{"AI coverCandidate references accepted image?"}
  cover -->|"no"| write
  cover -->|"yes"| guard["cover_guard black box<br/>ENABLE_COVER_CANDIDATE_GUARD default off"]
  guard --> generatedCover["Generate COVER image derivative"]
  generatedCover --> write["Update Recipe, Ingredients, Images,<br/>Sources, optional ReviewFlag"]
  write --> aggregate["Aggregate primary source status<br/>URL used if any child used<br/>URL ignored if all children ignored"]
  aggregate --> warn{"hasConflicts OR ignored primary source OR<br/>confidence <= IMPORT_WARN_CONFIDENCE?"}
  warn -->|"yes"| flag["Create CONTENT_WARNING flag"]
  warn -->|"no"| success
  flag --> success["Mark ImportJob succeeded<br/>createdRecipeId set"]
  success --> poll["Frontend polls GET /imports/{jobId}<br/>until terminal status"]
  failJob --> poll
  lowConfidence --> poll
  poll --> detail["GET /recipes/{id}<br/>returns sources, images, cover, flags"]

  classDef fail fill:#ffe0e0,stroke:#b91c1c,color:#111;
  classDef decision fill:#f3f4f6,stroke:#555,color:#111;
  classDef db fill:#e7f5ff,stroke:#1d4ed8,color:#111;
  classDef ai fill:#fff0b3,stroke:#b7791f,color:#111,stroke-width:2px;

  class fail400,failText,failFiles,failJob,lowConfidence fail;
  class validate,dedupe,url,quality,cover,warn decision;
  class persist,write,success db;
  class ai ai;
```

## Implemented Rules

- `clientImportId` deduplicates imports for the default local user.
- `POST /imports` processes synchronously for the local MVP and returns a terminal job when processing completes.
- Text input participates as recipe evidence.
- Attachments are accepted before URL images and occupy `MAX_IMPORT_IMAGES` capacity.
- URL images are loaded only within the remaining image capacity.
- URL loader order is Instagram, Threads, then generic fallback.
- `RecipeSource.source` records origin: `MANUAL`, `URL`, or `URL_VIDEO`.
- URL imports create a parent URL source plus child final sources for URL text, URL images, video transcript, and video poster.
- AI receives final sources only: all `RecipeSource` rows where `type != URL`, labeled with `RecipeSource.id`.
- Final recipe source statuses are derived from AI `primarySourceRefs` and `ignoredSourceRefs`.
- Primary URL source status is aggregated from children: used if any child is used, ignored if all children are ignored, otherwise unknown.
- Single URL import normalizes internal conflicts before warning/failure decisions, but source statuses still use the raw AI refs.
- `quality.confidence <= IMPORT_MIN_CONFIDENCE` fails the import and cleans saved files.
- Warning flags are created when `quality.hasConflicts`, any primary source is ignored, or `quality.confidence <= IMPORT_WARN_CONFIDENCE`.
- AI `coverCandidate` generates a separate cover derivative when it references an accepted image source.
- Cover candidate guard logic is isolated in `backend/app/imports/cover_guard.py` and remains default-off.

## Current Deferrals

- Real background queue/worker. The API contract already supports polling, but processing is sync-first.
- Real OpenAI provider wiring for production imports; tests/dev use the provider interface and fake provider.
- Video transcript/poster processing.
- Full live Instagram/Threads scraping resilience. Current platform loaders are isolated and fixture-tested.
- Cloud storage, auth, mobile-specific flows, and generated frontend API types.
