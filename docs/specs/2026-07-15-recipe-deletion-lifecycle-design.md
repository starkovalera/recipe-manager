# Recipe Deletion Lifecycle Design

## Goal

Make recipe deletion recoverable when filesystem cleanup fails by durably hiding the recipe before deleting its media and database row.

## Lifecycle

`Recipe.status` is a typed `RecipeStatus` with `ACTIVE` and `DELETION_PENDING`. Existing and newly created recipes default to `ACTIVE`.

`DELETE /recipes/{recipe_id}` first locks an owned `ACTIVE` recipe, changes it to `DELETION_PENDING`, and commits. From that point the recipe is absent from every product, search, collection, tag-count, and embedding query. The endpoint then attempts every recipe media deletion.

When every media deletion succeeds, a new transaction loads the pending recipe and physically deletes it. When any media deletion fails, the service logs sanitized diagnostics, leaves the recipe pending, and still returns `204`. Failure before the durable status transition continues to fail the request normally.

## Query Contract

Recipe-related query functions accept `status: RecipeStatus | None = RecipeStatus.ACTIVE`. A non-null status adds an explicit filter; `None` intentionally disables status filtering for maintenance workflows. Queries must build the SQLAlchemy statement before calling `session.scalar()` or `session.scalars()`.

The default active filter applies to recipe list/detail/mutation queries, collections and membership, tag recipe counts, autocomplete, exact and semantic search, Search Debug, embedding processing, and internal embedding lists. User-account deletion inventory intentionally includes recipes of every status.

## Embeddings

Embedding state does not duplicate recipe deletion state. Embedding queries and workers require an `ACTIVE` recipe. Physical recipe deletion removes its embedding and embedding events through existing cascades.

## Recovery

A scheduled maintenance job is future work. It will find stale `DELETION_PENDING` recipes using a current env-backed threshold, safely claim batches, retry media cleanup, and physically delete recipes only after cleanup succeeds.

## Verification

Tests cover migration defaults, active-by-default query behavior, successful deletion, partial storage failure, post-cleanup database failure, and exclusion of pending recipes from recipes, collections, tag counts, search, Search Debug, and embeddings.
