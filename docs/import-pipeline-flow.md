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

  H --> I["Build ready evidence in source order"]
  I --> J["Add text input as recipe evidence"]
  J --> K["Validate and save attachment images"]
  K --> L["Calculate remaining image capacity\nMAX_IMPORT_IMAGES - attachment count"]
  L --> M["Load URL content\nremote images only fill remaining capacity"]
  M --> N["Call AI recipe extraction provider"]

  N --> O{"AI result is recipe\nand confidence > min?"}
  O -- no --> P["Fail ImportJob\ncleanup saved media"]
  O -- yes --> Q["Normalize single-URL quality\nwhen applicable"]
  Q --> R["Create Recipe, ingredients,\nimages, sources"]

  R --> S["Source statuses from\nprimarySourceRefs / ignoredSourceRefs"]
  S --> T["Select coverCandidate from AI"]
  T --> U["Cover guard block\nfeature-flagged, default off"]
  U --> V["Generate cover image when candidate accepted"]
  V --> W{"hasConflicts OR hasIgnored OR\nconfidence <= IMPORT_WARN_CONFIDENCE?"}
  W -- yes --> X["Create open CONTENT_WARNING flag"]
  W -- no --> Y["No warning flag"]
  X --> Z["Mark ImportJob succeeded\ncreatedRecipeId=recipe.id"]
  Y --> Z

  E --> AA["Frontend polls GET /imports/{jobId}"]
  Z --> AA
  P --> AA
  AA --> AB{"Terminal status?"}
  AB -- succeeded --> AC["Redirect to recipe detail"]
  AB -- failed --> AD["Show import error"]
  AB -- pending/processing --> AA
```

Owner scoping is part of the current backend path: recipe, collection, and import endpoints resolve the current user through a single API dependency. Today that dependency returns the local default/admin user; later it can be replaced with authenticated user resolution without changing the service contracts.
