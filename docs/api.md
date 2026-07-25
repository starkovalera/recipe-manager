# Recipe Manager API

Current implemented API surface.

## Health

- `GET /health`
  - Response: `{ "status": "ok" }`

## Authentication and Current User

All routes except health, Clerk webhooks, and FastAPI documentation are protected by Clerk JWT validation at KrakenD. FastAPI receives only the verified provider subject and remains authoritative for internal-user status, roles, owner scoping, and business authorization.

- `POST /me/provision`
  - Explicitly resolves or creates the internal user for the verified subject.
  - Returns `201` when a new user, settings, and default tags are created atomically; repeated/existing-user calls return `200`.
  - Accepts no identity fields in the request body.
- `GET /me`
  - Requires an already provisioned active internal user.
  - Returns `{ id, email, features }`; features are backend-derived capabilities and roles are not exposed.
- `POST /me/deletion`
  - Atomically changes the current user to `DELETION_PENDING`, creates a pending `ACCOUNT_DELETION` outbox message, and returns `202` after attempting post-commit dispatch.
  - The final active superadmin cannot request deletion.
- `POST /webhooks/clerk`
  - Public at KrakenD, but requires a valid Svix signature over the raw body.
  - Idempotently processes `user.created`, `user.updated`, and `user.deleted` events.

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
  - Otherwise atomically marks embedding state as `stale` and creates a pending `RECIPE_EMBEDDING` outbox message, then attempts post-commit dispatch.
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
  - Atomically creates `ImportJob(status=queued)`, its initial audit/notification state, and a pending `IMPORT_JOB` outbox message, then attempts post-commit dispatch.
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
  - Requires `DEBUG` or `SUPERADMIN`.
  - Returns import jobs with owner/client ids, sources, status history, and job events.
  - `DEBUG` sees owned jobs; `SUPERADMIN` sees all jobs.
- `GET /internal/embeddings`
  - Requires `DEBUG` or `SUPERADMIN`.
  - Returns one row per existing `RecipeEmbedding`.
  - Rows include recipe embedding status, model, input hash, attempts, errors, timestamps, owner id, recipe title, and embedding event history.
  - Recipes without a `RecipeEmbedding` row are not returned.
  - Event history is internal audit/debug data only; current embedding status is read from `RecipeEmbedding.status`, not computed from events.
  - `DEBUG` sees owned recipe embeddings; `SUPERADMIN` sees all embeddings.
- `POST /internal/embeddings/{recipeId}/retry`
  - Requires `DEBUG` or `SUPERADMIN`; retry is allowed for an owned embedding or any embedding for `SUPERADMIN`.
  - Requests manual embedding retry for an existing `RecipeEmbedding` row.
  - Writes `retry_requested`, `scheduled`, and, if queueing succeeds, `enqueued` embedding events.
- `POST /internal/import-jobs/{jobId}/retry`
  - Requires `DEBUG` or `SUPERADMIN`; retry is allowed for an owned job or any job for `SUPERADMIN`.
  - Reuses the ordinary retry business flow and atomically creates a pending `IMPORT_JOB` outbox message with the accepted retry state.
- `POST /internal/search/explain`
  - Requires `DEBUG` or `SUPERADMIN`.
  - Accepts the same body shape as `POST /search`.
  - Returns effective filters, provider/model, candidate/result counts, ranked results, and debug distance/hash data where available.
  - Does not persist search debug snapshots.
  - `DEBUG` is owner-filtered; `SUPERADMIN` may inspect cross-user search results, but cannot open foreign ordinary recipe details.
- `GET /internal/access/users`
  - `SUPERADMIN` only. Returns paginated users, lifecycle status, fixed available roles/statuses, and role statistics.
  - Supports case-insensitive `q` search across email, internal user ID, and authentication-provider user ID.
  - Supports one `role` filter and one `status` filter; omitted filters include every role and status.
  - Supports `sortBy=email|createdAt|updatedAt`, `sortOrder=asc|desc`, `limit`, and `offset`.
  - Defaults to `updatedAt desc` with a stable user-ID tie-breaker.
- `PUT /internal/access/users/{userId}/roles/{role}`
  - `SUPERADMIN` only. Idempotently assigns a fixed role.
- `DELETE /internal/access/users/{userId}/roles/{role}`
  - `SUPERADMIN` only. Idempotently revokes a role except the final `SUPERADMIN` assignment.
- `PATCH /internal/access/users/{userId}/status`
  - `SUPERADMIN` only. Supports `ACTIVE` and `DEACTIVATED`; generic administration cannot set `DELETION_PENDING`.
- `GET /internal/invitations`
  - `SUPERADMIN` only. Returns sanitized local invitation history.
- `POST /internal/invitations`
  - `SUPERADMIN` only. Creates a Clerk invitation and stores sanitized metadata after provider success.
- `POST /internal/invitations/{invitationId}/revoke`
  - `SUPERADMIN` only. Idempotently revokes a pending invitation.

Recipe debug resources, embedding metadata, and embedding input are included only in owned recipe detail responses for users with `DEBUG`. The former standalone internal embedding-input endpoint has been removed.

## Authorization Boundary

- Ordinary recipes, media, collections, tags, notifications, imports, and search stay owner-scoped for every role.
- `SUPERADMIN` broadens explicitly approved internal diagnostics and administration only.
- `DEBUG` alone does not grant cross-user access.
- Frontend capability visibility is UX only; every backend endpoint enforces its own role and owner checks.

## Media Access

Recipe images and import image sources are represented by stable IDs. Public
domain responses do not contain storage keys or durable media URLs.

- `POST /media/access` accepts 1-100 `{type, id}` references and returns ordered
  per-item grants or indistinguishable `MEDIA_NOT_FOUND` errors.
- `GET /media/{media_type}/{media_id}` is the authenticated LOCAL retrieval
  endpoint and repeats ownership/lifecycle authorization.

S3 grants use `direct`; LOCAL grants use `authenticated_fetch`. These values
describe browser retrieval mechanics rather than provider or visibility. See
[`media-access.md`](media-access.md) for the complete contract.
