# Import Pipeline Flow

Current implementation is sync-first: `POST /imports` creates an `ImportJob`, processes it in the same request, and the frontend still polls `GET /imports/{jobId}` so the contract can move to a real background queue later.

```mermaid
flowchart TD
  A["Frontend submits import form\nclientImportId, text, url, files"] --> B["POST /imports"]
  B --> C["Resolve current user\nlocal default/admin user for now"]
  C --> D{"Existing ImportJob for\nowner_id + clientImportId?"}
  D -- yes --> E["Return existing ImportJob"]
  D -- no --> F["Create ImportJob\nstatus=pending"]
  F --> G["Persist import sources\nTEXT, IMAGE attachments, URL"]
  G --> H["Process job synchronously\nstatus=processing"]

  H --> I["Build RecipeSource tree\nprimary sources have no parent"]
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
  Y --> AA["Mark ImportJob succeeded\ncreatedRecipeId=recipe.id"]
  Z --> AA

  E --> AB["Frontend polls GET /imports/{jobId}"]
  AA --> AB
  P --> AB
  AB --> AC{"Terminal status?"}
  AC -- succeeded --> AD["Redirect to recipe detail"]
  AC -- failed --> AE["Show import error"]
  AC -- pending/processing --> AB
```

Owner scoping is part of the current backend path: recipe, collection, and import endpoints resolve the current user through a single API dependency. Today that dependency returns the local default/admin user; later it can be replaced with authenticated user resolution without changing the service contracts.
