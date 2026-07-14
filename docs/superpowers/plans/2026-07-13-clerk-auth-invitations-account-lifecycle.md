# Clerk Authentication, Invitations, and Account Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans`, the project backend/FastAPI skills, TDD, and `docs/refactoring-guidelines.md`. Stop at every iteration boundary for user review.

**Goal:** Complete Clerk-backed identity provisioning and account lifecycle management while preserving owner-scoped product behavior and local fixed roles.

**Architecture:** KrakenD validates Clerk session JWTs and forwards only trusted identity data. FastAPI separates trusted external identity, read-only current-user lookup, and explicit idempotent provisioning through `POST /me/provision`. Webhooks provide independent asynchronous lifecycle reconciliation; destructive local cleanup runs in an id-based Dramatiq task.

**Tech stack:** React 18, Vite, `@clerk/react`, TanStack Query, KrakenD Flexible Configuration, FastAPI, Pydantic v2, sync SQLAlchemy, PostgreSQL, Alembic, HTTPX, Svix verification, Dramatiq, Redis.

## Global Constraints

- Keep FastAPI on the host and retain the existing React/KrakenD/FastAPI/PostgreSQL/Redis/Dramatiq topology.
- Keep ordinary product endpoints owner-scoped, including for `SUPERADMIN`.
- Keep fixed `DEBUG` and `SUPERADMIN` roles in PostgreSQL; do not move them to Clerk metadata or JWT claims.
- Never persist raw Clerk JWTs, Bearer tokens, refresh tokens, session cookies, or invitation tickets.
- Do not add public registration, organizations, generic permissions, external admin frameworks, auth bypasses, or an `AUTH_MODE`.
- Do not change import, extraction, AI schemas, prompts, source statuses, review flags, covers, or queue business behavior.
- Use one request `SessionDep`; do not create a separate authentication session.
- `CurrentUserDep` remains the current-user dependency used by protected product handlers.
- Stop after this subphase for review and manual Clerk acceptance testing.

## Adaptations From The External v3 Instruction

The repository contains newer approved decisions that supersede provider-specific wording in the external instruction:

- Use `AuthProviderType`, `User.auth_provider`, and `User.auth_user_id`; do not restore `clerk_user_id` outside Clerk-specific client/payload code.
- Keep enum names and persisted values uppercase.
- KrakenD remains authoritative for Clerk issuer validation. FastAPI trusts only gateway-injected identity headers and does not require a backend `CLERK_ISSUER` setting or repeat issuer validation.
- Keep preview-only helpers and CLIs under `app/local` rather than spreading local-run code across production domain modules.
- Use the cached ordinary `get_auth_provider()` function; it is not a FastAPI dependency.

## Current Status

### Completed foundation

- [x] Added `@clerk/react`, a signed-out shell, `/sign-up` invitation path handling, in-memory token injection, and `UserButton` integration.
- [x] Centralized Bearer injection in `frontend/src/api/client.ts` without token persistence or logging.
- [x] Replaced static KrakenD configuration with Flexible Configuration templates and explicit route metadata.
- [x] Added production-safe uppercase `AppEnv`, Clerk/backend settings, and PREVIEW runtime behavior.
- [x] Added generic external identity fields, typed user lifecycle status, and migrations `0023`-`0025`.
- [x] Added validated PREVIEW TOML seeding, exact role synchronization, preview CLI, and role bootstrap CLI under `app/local`.
- [x] Added a focused HTTPX Clerk client with get-user and delete-user operations.
- [x] Added a lazily cached `get_auth_provider()` and tests proving provider reuse.
- [x] Added account-state and identity-related API error foundations.
- [x] Preserved local fixed roles, owner-scoped product access, and capability-based `GET /me` output.

### Partially complete and requiring correction

- [ ] Pass `VITE_CLERK_PUBLISHABLE_KEY` into `ClerkProvider`; the key is validated but is not currently passed to the component.
- [x] Replace hidden first-request provisioning inside `resolve_current_user()` with explicit provisioning.
- [x] Remove `AuthSessionDep`; auth and the route handler reuse the same `SessionDep`.
- [x] Close the read-only current-user transaction before handlers open their domain transaction, preserving the import-creation regression test for one request session.
- [ ] Extend the Clerk client/protocol with invitation operations and map provider failures to dedicated application errors.
- [ ] Extend KrakenD route metadata when each new route is added and make the webhook route public.
- [ ] Replace the current signed-in immediate app mount with the explicit provisioning bootstrap.

### Not yet implemented

- [x] Authenticated identity dependency and `USER_NOT_PROVISIONED` behavior.
- [x] `POST /me/provision`.
- [ ] Clerk webhooks and webhook idempotency storage.
- [ ] Invitations persistence, API, and UI.
- [ ] User activation/deactivation administration.
- [ ] `POST /me/deletion`, background user deletion, and reconciliation.
- [ ] Dedicated frontend provisioning/account-state/deletion screens.
- [ ] Final documentation and full verification.

---

## Iteration A: Identity Boundary And Read-Only Current User

**Files:**
- Modify: `backend/app/auth/types.py`
- Modify: `backend/app/auth/current_user.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/core/errors.py`
- Modify: `backend/tests/auth/test_current_user.py`
- Modify: `backend/tests/auth/test_provider.py`
- Modify: `backend/tests/api/test_imports_jobs.py`
- Create: `backend/tests/auth/test_dependencies.py`

**Produces:**

```python
@dataclass(frozen=True)
class AuthenticatedIdentity:
    auth_provider: AuthProviderType
    auth_user_id: str


AuthenticatedIdentityDep
CurrentUserDep
```

- [x] Add failing tests proving identity extraction performs no DB/provider work, missing mappings return `409 USER_NOT_PROVISIONED`, inactive statuses return their dedicated `403`, and known users resolve without provider calls.
- [x] Add a regression test proving `CurrentUserDep` and an import handler receive one shared session and authenticated import creation no longer raises `A transaction is already begun on this Session`.
- [x] Implement `get_authenticated_identity()` from trusted gateway headers without a database query or external provider call.
- [x] Make `get_current_user()` a read-only lookup by `(auth_provider, auth_user_id)` and remove user creation, provider calls, settings initialization, and role mutation from this path.
- [x] Remove `AuthSessionDep` and use the cached `SessionDep` in both auth and route dependencies.
- [x] Use an explicit short read transaction around current-user lookup so it is closed before a handler opens its domain transaction; do not add manual `commit()`/`rollback()` calls to route code.
- [x] Keep all existing protected route signatures based on `CurrentUserDep`.
- [x] Run focused identity/import regression tests and Ruff, then stop for review.

## Iteration B: Explicit User Provisioning And `/me` API

**Files:**
- Create: `backend/app/users/queries.py`
- Create: `backend/app/users/provisioning.py`
- Create: `backend/app/users/__init__.py`
- Modify: `backend/app/api/routes/users.py`
- Modify: `backend/app/schemas/users.py`
- Modify: `backend/app/db/init.py`
- Modify: `backend/app/core/errors.py`
- Modify: `backend/tests/auth/test_current_user.py`
- Create: `backend/tests/users/test_provisioning.py`
- Modify or create: `backend/tests/api/test_users.py`
- Modify: `infra/krakend/config/endpoints.json`
- Modify: `backend/tests/infra/test_krakend_config.py`

**Produces:**

```text
GET  /me
POST /me/provision
```

- [x] Write failing tests for the sequence `GET /me -> 409`, first provision `-> 201`, subsequent `GET /me -> 200`, repeated provision `-> 200`.
- [x] Test that provisioning accepts no identity body fields and derives identity only from `AuthenticatedIdentityDep`.
- [x] Extract one new-user creation use case that creates `User`, `UserSettings`, and default tags atomically with `ACTIVE` status and no roles.
- [x] Move default-tag initialization into that use case; PREVIEW seeding may reuse the same initialization behavior without changing configured IDs or exact roles.
- [x] Implement fast-path provisioning for an existing active user without a Clerk API call or settings/role changes.
- [x] For a missing user, call `get_auth_provider().get_user()` outside the database transaction, then create the local user atomically.
- [x] Handle concurrent provision calls and webhook races using the unique auth identity/email constraints plus explicit `IntegrityError` recovery.
- [x] Reject an email collision with a different identity using `409 EMAIL_ALREADY_LINKED`; never auto-link by email.
- [x] Centralize construction of the current-user response in the Pydantic output schema so `GET /me` and provisioning return the same capabilities shape.
- [x] Add `POST /me/provision` to protected KrakenD route metadata.
- [x] Run focused API/domain/gateway tests and Ruff, then stop for review. No migration was required for this iteration.

## Iteration C: Frontend Provisioning Bootstrap

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/app/ClerkApplication.tsx`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/queryClient.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/types.ts`
- Create or modify focused tests under `frontend/src/app/` and `frontend/src/api/`

- [ ] Pass the validated publishable key to `ClerkProvider`.
- [ ] Add an empty-body `provisionCurrentUser()` client call.
- [ ] After every established Clerk session, register the fresh-token provider, call provisioning, seed the `['current-user']` cache, and only then mount `App`.
- [ ] Prevent `/me`, notifications, recipes, and other protected queries while Clerk is loading, signed out, provisioning, or in a provisioning error state.
- [ ] Reset token provider, provisioning state, query cache, and app page on sign-out or Clerk identity/session change.
- [ ] Add dedicated screens for deactivated, deletion-pending, email-conflict, and retryable provider errors; retries must be explicit and finite.
- [ ] Test React Strict Mode/effect repetition, empty provisioning body, cache seeding, no premature product queries, and no token persistence.
- [ ] Run frontend tests, typecheck, and build, then stop for review.

## Iteration D: Shared Provisioning Semantics And Clerk Webhooks

**Files:**
- Extend: `backend/app/auth/types.py`
- Extend: `backend/app/auth/clerk_client.py`
- Create: `backend/app/auth/webhooks.py`
- Create: `backend/app/api/routes/webhooks.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20260714_0026_clerk_webhook_events.py`
- Modify: `backend/pyproject.toml` and lock data for the Svix verifier
- Modify: `infra/krakend/config/endpoints.json`
- Create: `backend/tests/auth/test_webhooks.py`
- Modify: `backend/tests/db/test_migrations.py`
- Modify: `backend/tests/infra/test_krakend_config.py`

- [ ] Add mocked Clerk client tests for the remaining provider contract and safe external-error mapping without sensitive payload logging.
- [ ] Add `ClerkWebhookEvent` idempotency storage and migration.
- [ ] Add public `POST /webhooks/clerk` with raw-body Svix verification and no `CurrentUserDep`.
- [ ] Implement idempotent `user.created`/`user.updated` synchronization through shared user provisioning/update semantics.
- [ ] Make webhook-first and explicit-provision-first orderings converge to the same user without duplicate defaults, role changes, or email auto-linking.
- [ ] Implement `user.deleted` as an idempotent transition to `DELETION_PENDING` plus deletion-task scheduling.
- [ ] Do not log raw webhook payloads, signatures, secrets, or authorization data.
- [ ] Mark the webhook route public in KrakenD and verify protected identity headers remain non-spoofable.
- [ ] Run webhook/domain/migration/gateway tests and Ruff, then stop for review.

## Iteration E: Invitations And User Status Administration

**Files:**
- Extend: `backend/app/auth/types.py`
- Extend: `backend/app/auth/clerk_client.py`
- Create: `backend/app/invitations/queries.py`
- Create: `backend/app/invitations/service.py`
- Create: `backend/app/invitations/__init__.py`
- Create: `backend/app/api/routes/invitations.py`
- Create: `backend/app/schemas/invitations.py`
- Modify: `backend/app/access/queries.py`
- Modify: `backend/app/access/rules.py`
- Modify: `backend/app/api/routes/access.py`
- Modify: `backend/app/schemas/access.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20260714_0027_invitations.py`
- Modify: `backend/app/main.py`
- Modify: `infra/krakend/config/endpoints.json`
- Create: `backend/tests/invitations/test_service.py`
- Create or modify API tests for invitations and access status changes
- Modify migration and gateway tests

- [ ] Add fixed invitation status enum/model without storing invitation tickets.
- [ ] Extend the Clerk client with create/list/revoke invitation operations and sanitized provider types.
- [ ] Add superadmin-only list/create/revoke invitation endpoints; normalize email, use configured frontend redirect URL, and make revoke idempotent.
- [ ] Mark a pending invitation accepted when `user.created` provisions the matching email.
- [ ] Include lifecycle status in access-user responses.
- [ ] Add idempotent `ACTIVE <-> DEACTIVATED` administration while forbidding generic transition to `DELETION_PENDING`.
- [ ] Prevent deactivation of the final active superadmin without changing role-management behavior.
- [ ] Add every endpoint to protected KrakenD metadata.
- [ ] Run invitation/access/migration/gateway tests and Ruff, then stop for review.

## Iteration F: User-Initiated And Background Deletion

**Files:**
- Create: `backend/app/users/deletion.py`
- Create: `backend/app/users/tasks.py`
- Modify: `backend/app/api/routes/users.py`
- Modify: `backend/app/schemas/users.py` if a response body is required by the final API contract
- Modify: `backend/app/worker.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/core/errors.py`
- Modify: `infra/krakend/config/endpoints.json`
- Create: `backend/tests/users/test_deletion.py`
- Create: `backend/tests/api/test_users.py`
- Modify: `backend/tests/infra/test_krakend_config.py`

- [ ] Add idempotent protected `POST /me/deletion` for active users.
- [ ] Prevent deletion of the only active superadmin.
- [ ] Delete the external provider identity, persist `DELETION_PENDING` and timestamp durably, then enqueue the local deletion actor.
- [ ] Make later `user.deleted` webhook processing safely repeat the transition/enqueue flow.
- [ ] Implement an id-only Dramatiq actor that reloads the user, verifies status, collects only that user's storage keys, deletes owned DB data transactionally, and removes media idempotently.
- [ ] Collect the complete current storage inventory from `RecipeImage.storage_key` through the user's recipes and `ImportJobSource.image_storage_key` through the user's import jobs; `RecipeResource` adds no separate storage key.
- [ ] Add actor-specific retry configuration and a reconciliation command for pending users after restart.
- [ ] Add `POST /me/deletion` to protected KrakenD metadata.
- [ ] Run deletion/API/worker/gateway tests and Ruff, then stop for review.

## Iteration G: Admin And Account Lifecycle UI

**Files:**
- Modify: `frontend/src/pages/AdminPage.tsx`
- Create: `frontend/src/pages/InvitationsPage.tsx`
- Modify: `frontend/src/pages/RoleManagementPage.tsx`
- Modify: `frontend/src/app/ClerkApplication.tsx`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/pages/RoleManagementPage.test.tsx`
- Create: `frontend/src/pages/InvitationsPage.test.tsx`
- Create: `frontend/src/app/ClerkApplication.test.tsx`

- [ ] Add an Invitations admin tab, rendered from backend capabilities, with history/create/revoke controls and no Clerk ticket/secret display.
- [ ] Add activate/deactivate controls and lifecycle status to existing role management UI.
- [ ] Add an irreversible asynchronous Delete Account confirmation and call `POST /me/deletion`.
- [ ] After accepted deletion, clear query/token state, sign out through Clerk, and show a neutral completion screen.
- [ ] Preserve dedicated deactivated and deletion-pending screens instead of mounting the product.
- [ ] Keep all identity/provider operations behind the application backend.
- [ ] Run frontend tests, typecheck, and build, then stop for review.

## Iteration H: Documentation, Reconciliation, And Closeout

**Files:**
- Modify: `README.md`
- Modify: `backend/.env.example`
- Modify: `frontend/.env.example`
- Modify: `backend/config/preview-users.example.toml`
- Modify: `infra/krakend/README.md`
- Create or modify: `docs/manual-testing/` Clerk lifecycle instructions
- Modify: `docs/background-processing-plan.md`
- Modify: `docs/invariants.md`
- Modify: `docs/future-work.md`
- Update this plan's final statuses

- [ ] Document Clerk CLI setup, env names, invite-only flow, startup order, webhook relay, role bootstrap, explicit provisioning, PREVIEW seed behavior, deletion worker, and direct-FastAPI local limitation without real keys.
- [ ] Run full backend pytest, Ruff check/format, frontend tests/typecheck/build, migration tests, `docker compose config`, and KrakenD build/render validation.
- [ ] Reconcile every FastAPI route/method with gateway metadata and verify public/protected classification.
- [ ] Re-check owner isolation, local roles, no-token persistence, import invariants, and `docs/refactoring-guidelines.md`.
- [ ] Review relevant future-work items and move only actually completed items out of `docs/future-work.md`.
- [ ] Report manual Clerk checks still required; do not claim real email, webhook, sign-in, invitation, or deletion success without user verification.
- [ ] Propose invariant and future-work updates, wait for approval, update documents, and stop for subphase review.

## Relevant Existing Future Work

- Move default-tag initialization into the single new-user creation use case. This is included in Iteration B.
- Distinguish user-triggered and admin-triggered import retries and define notification/audit behavior. Authentication enables this distinction, but changing import retry semantics is not included in this subphase unless separately approved.
- Expose backend-owned recipe editing limits instead of independent frontend environment values. This belongs to user settings/capabilities work but is not required by Clerk Phase A.
- Scheduled failed-import/orphan-media cleanup remains separate from account deletion. The deletion actor must still clean media owned by the deleted user.
- Broader auth/admin visual polish remains in the later UI/UX design phase.

## Approval Blocks

- Before Iteration A, approve the shared-session transaction strategy: identity has no session; current-user lookup uses one short explicit read transaction on the same request session, followed by independent handler transaction scopes.
- Before Iteration D, confirm the selected Svix verification dependency/version after checking current official Clerk guidance.
- Before Iteration F, review the exact owned-data/storage inventory and deletion order before destructive lifecycle code is implemented.
- Manual Clerk acceptance testing is required after Iterations C, D, E, and G.
