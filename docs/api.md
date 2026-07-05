# Recipe Manager API

Current implemented API surface.

## Health

- `GET /health`
  - Response: `{ "status": "ok" }`

## Recipes

- `GET /recipes?limit=24&offset=0`
  - Returns `{ items: [{ id, title, note, updatedAt, coverImage, hasOpenReviewFlags }], total, limit, offset }`.
  - Optional structured filters:
    - `tag=<tagId>`
    - `ingredientQuery=<text>`; may be repeated, each value requires at least one ingredient whose `search_name` contains the normalized query text
    - `sourceName=MANUAL|INSTAGRAM|THREADS|TT|OTHER`
    - `authorName=<author name>`
    - `title=<recipeId from title suggestion>`
- `GET /recipes/{recipeId}`
  - Returns recipe detail with ingredients, instructions, tags as `{ id, name, description, deletedAt }`, sources, and review flags.
- `PATCH /recipes/{recipeId}`
  - Supports `title`, `servings`, `cookTimeMinutes`, `instructions`, `note`, and `tagIds`.
  - `tagIds` must reference active current-user tags; recipe edit does not create tags.
  - Validates recipe size against `MAX_RECIPE_INGREDIENTS`, `MAX_RECIPE_INSTRUCTION_CHARS`, and `MAX_RECIPE_NOTE_CHARS`.
- `PATCH /recipes/{recipeId}/review-flags/{flagId}`
  - Body: `{ "status": "open" | "resolved" }`.
- `POST /recipes/{recipeId}/embedding/retry`
  - Retries embedding generation for the current-user recipe.
  - If the recipe has open review flags, marks embedding state as `skipped_due_to_flags` and does not enqueue work.
  - Otherwise marks embedding state as `stale` and enqueues `embed_recipe_task`.
  - Returns `{ recipeId, status, model, inputHash, failedAttempts, errorMessage }`.

## Collections

- `GET /collections?limit=24&offset=0`
  - Returns `{ items: [{ id, name, description, recipeCount }], total, limit, offset }`.
- `POST /collections`
  - Body: `{ "name": string, "description"?: string | null }`.
- `GET /collections/{collectionId}`
  - Returns collection detail with recipe tiles.
- `DELETE /collections/{collectionId}`
  - Deletes the collection.
- `PUT /collections/{collectionId}/recipes/{recipeId}`
  - Adds a recipe to the collection.
- `DELETE /collections/{collectionId}/recipes/{recipeId}`
  - Removes a recipe from the collection.

## Tags

- `GET /tags?limit=24&offset=0`
  - Returns active current-user tags only: `{ items, total, limit, offset }`.
  - `items`: `[{ id, name, description, deletedAt }]`.
- `POST /tags`
  - Body: `{ "name": string, "description"?: string | null }`.
  - Enforces `MAX_TAGS_PER_USER`.
  - Rejects duplicate active tag names case-insensitively.
- `PATCH /tags/{tagId}`
  - Body: `{ "name"?: string, "description"?: string | null }`.
  - Updates active current-user tags.
  - Omitting `description` preserves it; sending `description: null` clears it.
- `GET /tags/{tagId}/usage`
  - Returns `{ recipeCount }` for current-user recipes linked to the tag.
- `DELETE /tags/{tagId}`
  - Soft-deletes the tag with `deletedAt`.
  - Preserves existing `recipe_tags` links.

## Search

- `POST /search`
  - Body: `{ "text"?: string | null, "selected"?: SearchChip[], "limit"?: number, "offset"?: number }`.
  - `SearchChip.type`: `tag`, `ingredient_query`, `source_name`, `author_name`, or `title`.
  - Returns `{ items: [{ id, title, note, coverImage, hasOpenReviewFlags, matchReasons }], limit, offset, hasMore }`.
  - Uses `hasMore`, not `total`.
  - Free text is semantic/vector search only and searches current-user recipes with `RecipeEmbedding.status = ready`.
  - Selected chips are hard filters. With both text and chips, filters are applied before vector ranking.
  - Without text, selected chips return matching recipes sorted by the default recipe order.
  - Without text and without selected chips, the frontend continues using `GET /recipes` for the default recipe grid.
  - Recipes without ready embeddings, including `skipped_due_to_flags`, are absent from semantic results.
- `GET /search/suggestions?q=<text>&limit=10`
  - Returns `{ items: [{ type, id, recipeId, value, label }] }`.
  - Suggestion `type` values: `tag`, `ingredient_query`, `source_name`, `author_name`, `title`.
  - `ingredient_query` is a primary text-based ingredient filter suggestion derived from the user's current query text, not from a concrete ingredient row.
  - Sources are direct current-user table values only: active `tags.name`, `recipes.source_name`, `recipes.author_name`, and `recipes.title`. Ingredient suggestions use the current query as an `ingredient_query` action.
  - Collections, recent searches, search suggestion tables, and canonical ingredient aliases are not included.

## Imports

- `POST /imports`
  - Multipart form fields: `clientImportId`, optional `text`, optional `url`.
  - Headers: `X-Client-Id`, optional `Idempotency-Key`.
  - Creates `ImportJob(status=queued)` and enqueues `import_recipe_task`.
  - Returns `202 Accepted` for a newly queued import.
  - Returns `200 OK` when the same dedupe key already exists and the existing job is returned.
  - Returns `{ jobId, status, createdRecipeId, errorCode, errorMessage }`.
  - Status values: `queued`, `running`, `succeeded`, `succeeded_with_flags`, `failed`, `cancelled`.
- `GET /imports/{jobId}`
  - Polling endpoint returning the same job shape.

## Notifications

- `GET /notifications`
  - Returns `{ items: [{ id, type, status, title, message, entityType, entityId, data, readAt, createdAt, updatedAt }] }`.
  - Used by the frontend for polling, toast display, and notification history.
- `PATCH /notifications/{notificationId}`
  - Body: `{ "status": "read" | "unread" }`.
  - Marks a notification read/unread for the current user.
- `PATCH /notifications/read-all`
  - Body: `{ "lastNotificationId": "<notification id from current frontend snapshot>" }`.
  - Finds that notification for the current user, uses its `createdAt` as the cutoff, and marks unread notifications with `createdAt <= cutoff` as read.
  - Returns `{ updatedCount }`.

## Internal

- `GET /internal/import-jobs`
  - Internal diagnostics endpoint for the current local/admin workflow.
  - Returns import jobs with owner/client ids, sources, status history, and job events.
  - Real admin-only authorization is deferred to Phase 5.
- `GET /internal/embeddings`
  - Internal diagnostics endpoint for the current local/admin workflow.
  - Returns one row per existing `RecipeEmbedding`.
  - Rows include recipe embedding status, model, input hash, attempts, errors, timestamps, owner id, recipe title, and embedding event history.
  - Recipes without a `RecipeEmbedding` row are not returned.
  - Event history is internal audit/debug data only; current embedding status is read from `RecipeEmbedding.status`, not computed from events.
  - Real admin-only authorization is deferred to Phase 5.
- `POST /internal/embeddings/{recipeId}/retry`
  - Internal diagnostics action for the current local/admin workflow.
  - Requests manual embedding retry for an existing `RecipeEmbedding` row.
  - Writes `retry_requested`, `scheduled`, and, if queueing succeeds, `enqueued` embedding events.
  - Real admin-only authorization is deferred to Phase 5.
- `POST /internal/search/explain`
  - Admin-only diagnostics endpoint for semantic search debugging.
  - Accepts the same body shape as `POST /search`.
  - Returns effective filters, provider/model, candidate/result counts, ranked results, and debug distance/hash data where available.
  - Does not persist search debug snapshots.
- `GET /internal/recipes/{recipeId}/embedding-input`
  - Admin-only diagnostics endpoint.
  - Returns the current embedding input text and hash for one recipe.
  - Uses the same embedding input builder that embedding jobs use.

## Current Deferrals

- Dedicated multi-user authorization is deferred to Phase 5.
- Internal/admin pages are visible in the local/admin workflow until Phase 5 role checks are implemented.
