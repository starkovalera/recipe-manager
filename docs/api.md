# Recipe Manager API

Current implemented API surface.

## Health

- `GET /health`
  - Response: `{ "status": "ok" }`

## Recipes

- `GET /recipes`
  - Returns `{ items: [{ id, title, note, updatedAt }] }`.
- `GET /recipes/{recipeId}`
  - Returns recipe detail with ingredients, instructions, sources, and review flags.
- `PATCH /recipes/{recipeId}`
  - Supports `title`, `servings`, `cookTimeMinutes`, `instructions`, and `note`.
  - Validates recipe size against `MAX_RECIPE_INGREDIENTS`, `MAX_RECIPE_INSTRUCTION_CHARS`, and `MAX_RECIPE_NOTE_CHARS`.
- `PATCH /recipes/{recipeId}/review-flags/{flagId}`
  - Body: `{ "status": "open" | "resolved" }`.

## Imports

- `POST /imports`
  - Multipart form fields: `clientImportId`, optional `text`, optional `url`.
  - Header: `X-Client-Id`.
  - Current implementation processes text/URL evidence with the fake extraction provider.
  - Returns `{ jobId, status, createdRecipeId, errorCode, errorMessage }`.
- `GET /imports/{jobId}`
  - Polling endpoint returning the same job shape.

## Current Deferrals

- Uploaded file import route parsing is not wired yet.
- Platform URL loaders are not wired yet.
- Real OpenAI extraction/transcription provider is not wired yet.
- Import worker is persisted by `ImportJob`, but current processing runs immediately in the request path for the first vertical slice.
- Media serving route is not wired yet.
