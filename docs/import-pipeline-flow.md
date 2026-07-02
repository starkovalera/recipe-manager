# Import Pipeline Flow

Current backend implementation is queue-first: `POST /imports` creates an `ImportJob`, enqueues Dramatiq work, and returns `202 Accepted`. The worker processes the import in the background. Frontend polling UX is still Phase 1d.

```mermaid
flowchart TD
  A["Frontend submits import form\nclientImportId, text, url, files"] --> B["POST /imports"]
  B --> C["Resolve current user\nlocal default/admin user for now"]
  C --> D{"Existing ImportJob for\nowner_id + dedupe_key?"}
  D -- yes --> E["Return existing ImportJob"]
  D -- no --> F["Create ImportJob\nstatus=queued\nrecord import_started notification"]
  F --> G["Persist import sources\nTEXT, IMAGE attachments, URL\nrecord queued event"]
  G --> H["Enqueue import_recipe_task\nreturn 202 Accepted"]
  H --> HW["Dramatiq worker\nprocesses sync handler\nstatus=running\nrecord worker_started event"]

  HW --> I["Build RecipeResource tree\nprimary resources have no parent"]
  I --> J["Manual text/image\nsource=MANUAL, final evidence"]
  J --> K["URL row\nsource=MANUAL, type=URL, primary only"]
  K --> L["Load URL content\nrespect remaining image capacity"]
  L --> M["Create URL children\nTEXT/IMAGE source=URL\ntranscript/poster source=URL_VIDEO"]
  M --> N["Call AI with final sources only\ntype != URL, id=source_N"]

  N --> O{"AI result is recipe\nand confidence > min?"}
  O -- no --> P["Fail ImportJob\ncleanup saved media"]
  O -- yes --> Q["Normalize single-URL quality\nwhen applicable"]
  Q --> R["Update Recipe, ingredients,\nimages, sources"]

  R --> S["Final source statuses from\nprimarySourceRefs / ignoredSourceRefs"]
  S --> T["Select coverCandidate from AI"]
  T --> U["Cover guard block\nfeature-flagged, default off"]
  U --> V["Generate cover image when candidate accepted"]
  V --> W["Aggregate primary URL status\nused if any child used\nignored if all children ignored"]
  W --> X{"hasConflicts OR ignored primary OR\nconfidence <= IMPORT_WARN_CONFIDENCE?"}
  X -- yes --> Y["Create open CONTENT_WARNING flag"]
  X -- no --> Z["No warning flag"]
  Y --> AA["Mark ImportJob succeeded_with_flags\ncreatedRecipeId=recipe.id\nrecord notification"]
  Z --> AB0["Mark ImportJob succeeded\ncreatedRecipeId=recipe.id\nrecord notification"]

  E --> AB["Frontend polls GET /imports/{jobId}"]
  AA --> AB
  AB0 --> AB
  P --> AB
  AB --> AC{"Terminal status?"}
  AC -- succeeded --> AD["Redirect to recipe detail"]
  AC -- succeeded_with_flags --> AD
  AC -- failed --> AE["Show import error"]
  AC -- queued/running --> AB
```

Owner scoping is part of the current backend path: recipe, collection, and import endpoints resolve the current user through a single API dependency. Today that dependency returns the local default/admin user; later it can be replaced with authenticated user resolution without changing the service contracts.
