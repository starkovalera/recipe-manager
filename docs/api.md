# Recipe Manager API

Current implemented API surface.

## Health

- `GET /health`
  - Response: `{ "status": "ok" }`

## Recipes

- `GET /recipes`
  - Returns `{ items: [{ id, title, note, updatedAt }] }`.
- `GET /recipes/{recipeId}`
  - Returns recipe detail with ingredients, instructions, tags as `{ id, name, description, deletedAt }`, sources, and review flags.
- `PATCH /recipes/{recipeId}`
  - Supports `title`, `servings`, `cookTimeMinutes`, `instructions`, `note`, and `tagIds`.
  - `tagIds` must reference active current-user tags; recipe edit does not create tags.
  - Validates recipe size against `MAX_RECIPE_INGREDIENTS`, `MAX_RECIPE_INSTRUCTION_CHARS`, and `MAX_RECIPE_NOTE_CHARS`.
- `PATCH /recipes/{recipeId}/review-flags/{flagId}`
  - Body: `{ "status": "open" | "resolved" }`.

## Tags

- `GET /tags`
  - Returns active current-user tags only: `{ items: [{ id, name, description, deletedAt }] }`.
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

## Current Deferrals

- Dedicated multi-user authorization is deferred to Phase 5.
- Internal/admin pages are visible in the local/admin workflow until Phase 5 role checks are implemented.
