# Recipe Deletion Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a recoverable two-stage recipe deletion lifecycle that hides pending recipes and preserves them for later cleanup when media deletion fails.

**Architecture:** `Recipe.status` is the single lifecycle source of truth. Query functions explicitly filter active recipes by default, while deletion uses short transactions around the durable status transition and final database delete with filesystem work between them.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL/SQLite tests, pytest, Ruff.

## Global Constraints

- Keep ordinary recipe data owner-scoped.
- Return `204` once `DELETION_PENDING` is durably committed, even when media cleanup fails.
- Do not add a duplicate deletion status to `RecipeEmbedding`.
- Do not change frontend API response schemas.
- Preserve account deletion access to media from recipes of every status.

---

### Task 1: Recipe Status Persistence

**Files:**
- Modify: `backend/app/models/__init__.py`
- Create: next migration under `backend/alembic/versions/`
- Modify: `backend/tests/db/test_migrations.py`

- [x] Add failing model and migration assertions for `ACTIVE` default and the typed status column.
- [x] Run focused tests and verify the expected failure.
- [x] Add `RecipeStatus`, `Recipe.status`, and the PostgreSQL/SQLite-compatible migration.
- [x] Run focused tests and verify they pass.

### Task 2: Active Recipe Query Boundary

**Files:**
- Modify: `backend/app/recipes/queries.py`
- Modify: `backend/app/search/queries.py`
- Modify: `backend/app/collections/queries.py`
- Modify: `backend/app/tags/queries.py`
- Modify: `backend/app/embeddings/queries.py`
- Modify focused query/API tests in the matching `backend/tests/` domains.

- [x] Add failing tests showing pending recipes are absent from recipe APIs, collections, tag counts, search/autocomplete, Search Debug, and embeddings.
- [x] Run focused tests and verify the expected failures.
- [x] Add explicit `RecipeStatus | None = RecipeStatus.ACTIVE` filters at the query boundary.
- [x] Run focused tests and verify they pass.

### Task 3: Two-Stage Recipe Deletion

**Files:**
- Modify: `backend/app/services/recipes.py`
- Modify: `backend/app/recipes/queries.py`
- Modify: `backend/tests/api/test_recipes.py`

- [x] Add failing tests for durable pending transition, successful cleanup/final delete, partial storage failure, and final database failure.
- [x] Run focused tests and verify the expected failures.
- [x] Implement row-locked active-to-pending transition, out-of-transaction media cleanup, and a separate pending-row delete transaction.
- [x] Keep cleanup failures logged and return normally after the pending transition.
- [x] Run focused tests and verify they pass.

### Task 4: Documentation And Verification

**Files:**
- Modify: `docs/future-work.md`
- Propose updates to `docs/background-processing-plan.md` after implementation review.

- [x] Add the scheduled stale pending-recipe cleanup job to future work.
- [x] Run `uv run ruff check app tests`.
- [x] Run Ruff format checks for every changed Python file.
- [x] Run full `uv run pytest -q`.
- [x] Run `git diff --check` and review against `docs/refactoring-guidelines.md`.
- [ ] Propose invariant updates and stop for user review before committing implementation.
