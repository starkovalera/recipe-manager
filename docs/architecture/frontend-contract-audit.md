# Reusable Non-Visual Frontend Contract Audit

Status: completed 2026-08-14<br>
Scope: issue [#24](https://github.com/starkovalera/recipe-manager/issues/24)<br>
Workstream: Development / frontend contract discovery

This audit evaluates the current React/Vite frontend as a source of reusable
behavior for the future redesign/rewrite. It does not approve the current
shell, visual components, CSS, route layout, or prototypes as implementation
sources. The canonical product and architecture contracts remain the API,
authentication, media-access, import-pipeline, and accepted ADR documents
linked below.

This is a V1 web/shared-contract input. Any future mobile consumer belongs to
the V2 planning iteration; this audit does not authorize mobile Development or
make mobile work a V1 release blocker.

## Classification

- **Retain** — the behavior is a stable contract with clear ownership and
  sufficient evidence to carry into a new client.
- **Refactor before reuse** — the behavior is valuable, but its current
  ownership, typing, lifecycle policy, or test seam is too coupled to the
  current application to copy directly.
- **Replace** — the current implementation is an incidental mechanism or a
  duplicated source of truth and should have a new implementation behind the
  same or an explicitly revised contract.
- **Design-gated** — implementation depends on an approved Core Design
  Baseline or Operational Surfaces Addendum and must not be inferred from the
  current UI.

## Executive conclusion

The future client should preserve one backend/API contract for web and mobile,
the in-memory Clerk token boundary, explicit first-login provisioning, auth
cache clearing, owner-scoped media references, media grant retrieval modes,
and the import-job state machine. These behaviors are described by the
project contracts and exercised by focused frontend/backend tests.

The current frontend is not a reusable visual foundation. It is an in-memory
single-page shell with page-local navigation, page-local formatting and error
maps, manually duplicated API types, scattered React Query keys, and a jsdom
test setup without a browser E2E harness. The redesign should extract the
behavioral contracts behind new boundaries and reimplement the shell, route
presentation, visual components, responsive states, copy, and accessibility
interaction patterns from approved design evidence.

No production behavior is changed by this audit.

## Reuse matrix

| Boundary | Classification | Evidence and known consumers | Coupling risks and reuse conditions |
| --- | --- | --- | --- |
| Clerk session, token, and first-login provisioning lifecycle | **Retain** the contract; **refactor before reuse** of the component | `frontend/src/app/ClerkApplication.tsx:33-117` installs an in-memory token provider, provisions every new Clerk session, seeds `current-user`, and clears the token/cache on unmount or identity change. The API transport requests a fresh token in `frontend/src/api/client.ts:79-118`. Consumers include `App`, all API calls, and authenticated media. `frontend/src/app/ClerkApplication.test.tsx:91-199` covers ordering, Strict Mode replay, retry, unmount, user changes, and session changes. The canonical flow is [`authentication-and-authorization.md`](../authentication-and-authorization.md#request-authentication-flow). | Keep the token provider and provisioning/cache invariants. Do not carry over the combined Clerk UI, account-deletion UI, and shell mounting structure. The backend remains authoritative for active-user status, roles, capabilities, and owner authorization; frontend capability visibility is not security. |
| Authenticated routing and page navigation | **Replace** the current mechanism; **design-gated** for the replacement experience | `frontend/src/app/App.tsx:17-30` stores a `Page` union in component state and `:45-135` renders all navigation and page transitions through `setPage`. `frontend/src/app/ClerkApplication.tsx:14-30` special-cases only `/sign-up`. There is no router dependency in `frontend/package.json`. `App` tests exercise transitions, but not browser URL/deep-link/reload behavior. | The `Page` union and current tab/header layout are not a durable route contract. A replacement may preserve route identities and recipe/import/collection IDs, but URL ownership, browser history, mobile navigation, focus restoration, and visual shell behavior require the approved design and implementation handoff. |
| API transport, auth header, response parsing, and error mapping | **Refactor before reuse** | `frontend/src/api/client.ts:35-141` centralizes the API base URL, per-request bearer token, fetch boundary, JSON/204 parsing, media fetches, debug logging, and `ApiError`. Every API wrapper in `frontend/src/api/client.ts:159-394` uses this boundary. `frontend/src/api/client.test.ts:39-100` and `:138-167` cover fresh tokens, protected media, backend error payloads, empty 204 responses, and media requests. | Preserve the single transport boundary and safe logging rules, but do not copy the untyped parser as a final client contract. `ApiError.errorCode` is an unrestricted string, malformed/non-JSON errors are not normalized, network failures have no stable category, and field-level validation or retry metadata is absent. The client also owns a large manually maintained endpoint wrapper file. |
| API response/request types and schema ownership | **Replace** manual duplication with generated or validated types; **refactor before reuse** of local domain types | `frontend/src/api/types.ts:1-374` is the central shared frontend type source and is manually duplicated from the FastAPI schemas; additional endpoint input types are declared inline in the client and pages. Backend schemas use the camel-case boundary in `backend/app/schemas/base.py:4-16`, with representative contracts in `backend/app/schemas/recipes.py:26-276`, `backend/app/schemas/imports.py:10-34`, and `backend/app/schemas/media.py:10-50`. No frontend OpenAPI/code-generation configuration was found. The import pipeline explicitly lists generated frontend API types as deferred work in [`import-pipeline.md`](../import-pipeline.md#current-deferrals). | Drift is already observable: `RecipePatch` omits backend-supported `servings` (`frontend/src/api/types.ts:352-363` vs `backend/app/schemas/recipes.py:234-247`); recipe resources omit backend `position`, assessment reason, and confidence (`frontend/src/api/types.ts:300-310` vs `backend/app/schemas/recipes.py:50-62`); several frontend fields widen backend constrained values to `string`; and the public API documentation omits terminal `failed_artifacts_removed` even though the frontend models it and maintenance can produce it. Add one schema source/generation or runtime validation boundary before redesign clients multiply the drift. |
| TanStack Query client, keys, invalidation, polling, and mutation semantics | **Refactor before reuse** | The singleton client is `frontend/src/app/queryClient.ts:1-3`. Global current-user and notification queries are in `frontend/src/app/App.tsx:31-36`; notifications poll every five seconds. Recipe/search queries and suggestions are in `frontend/src/pages/RecipeListPage.tsx:41-49`. Recipe mutations and their invalidations are in `frontend/src/pages/RecipeDetailPage.tsx:163-237`; collection/tag/admin mutations have similar local policies. Import detail polling and retry cache updates are in `frontend/src/pages/ImportJobDetailPage.tsx:48-60`. Media grant expiry polling is in `frontend/src/media/useMediaAccess.ts:21-30`. | Query keys are string literals with inconsistent naming and shape (`recipes`, `recipeSearch`, `searchSuggestions`, `recipe`, `collection`, `internal-*`). Invalidation is duplicated and can be incomplete when a mutation affects several projections. Query defaults are not explicitly owned, and `InternalEmbeddingsPage.tsx:15-18` imports the singleton directly while other pages use `useQueryClient`. Preserve the documented polling and cache-clearing behavior, then centralize key factories, auth scoping, defaults, invalidation policy, and lifecycle tests. |
| Media references, batch grants, direct URLs, authenticated fetches, and object URLs | **Retain** the contract; **refactor before reuse** of the current component implementation | Stable `(type, id)` references, ordered partial results, grant modes, expiry refresh, and object-URL cleanup are documented in [`media-access.md`](../media-access.md#frontend-responsibilities). `frontend/src/media/useMediaAccess.ts:10-46` deduplicates references, requests grants, refreshes expiring grants, and exposes `grantFor`. `frontend/src/components/MediaImage.tsx:13-35` separates direct `<img>` URLs from authenticated Blob fetches and revokes object URLs. Consumers are `RecipeGrid`, `RecipeDetailPage`, and `ImportJobDetailPage`; focused tests are `frontend/src/media/useMediaAccess.test.ts:5-21` and `frontend/src/components/MediaImage.test.tsx:20-44`. | Preserve the security and lifecycle invariants: no storage keys in the client, bearer tokens for authenticated fetches, direct grants only as retrieval details, partial success, and revocation on replacement/unmount. Before reuse, add a canonical cache-key policy independent of input ordering, explicit per-item error/fallback behavior, expiry/refetch tests, and image-load failure handling. Keep the retrieval behavior separate from visual image presentation. |
| Import submission, job polling, terminal states, notifications, and manual retry | **Retain** the backend-driven lifecycle; **refactor before reuse** of page-local presentation/error maps | `frontend/src/pages/ImportPage.tsx:17-33` creates a new client import ID, submits multipart data, clears the form after acceptance, and intentionally does not poll. `frontend/src/pages/ImportJobDetailPage.tsx:11-76` polls only `queued`/`running`, maps terminal states, and retries only a failed job below the current attempt limit. `frontend/src/pages/InternalImportJobsPage.tsx:5-66` exposes technical history and the internal retry seam. The public and internal paths are covered by `ImportPage.test.tsx`, `ImportJobDetailPage.test.tsx`, and `App.test.tsx`. The queue-first behavior and user navigation are canonical in [`import-pipeline.md`](../import-pipeline.md#jobs-retry-and-user-navigation). | Keep the distinction between accepted submission, notification-driven completion, user-safe detail, and admin-only event data. The current status labels and `ERROR_MESSAGES` table are local to one page, while the backend error policy is the source of truth in [`import-error-handling.md`](../import-error-handling.md#stable-error-policy). The frontend should consume a typed status/error policy and explicitly include `FAILED_ARTIFACTS_REMOVED`, a terminal non-retryable state. |
| Formatting, localization, and date/number presentation | **Replace** page-local helpers with a shared contract; **design-gated** for language and copy decisions | Date formatting is duplicated in `ImportJobDetailPage.tsx:33-35`, `InternalImportJobsPage.tsx:7-9`, `InternalEmbeddingsPage.tsx:6-8`, `NotificationsPage.tsx:6-8`, and `UsersPage.tsx:10-12`. Internal search has another local number formatter in `InternalSearchDebugPage.tsx:20-24`. All use browser-default `toLocaleString()` or ad hoc fallback text; no locale provider, timezone policy, translation catalog, or shared formatter exists. | A shared formatter can be a non-visual seam, but its locale, timezone, missing-value, precision, and stable-test contract must be decided before implementation. Do not infer product language, copy, or locale selection from the current English strings. The authentication document records mandatory immutable language selection as deferred product work. |
| Accessibility primitives and state announcements | **Design-gated** for the replacement component system; **refactor before reuse** of selected semantic conventions | The current UI uses native labels/buttons plus isolated `aria-label`, `role="alert"`, `role="status"`, `role="dialog"`, and `aria-pressed` attributes across `App.tsx`, `ClerkApplication.tsx`, `RecipeDetailPage.tsx`, and list/admin pages. Tests query several accessible names and roles, including account deletion in `ClerkApplication.test.tsx` and page flows in `App.test.tsx`. | Retain the requirement that loading, error, empty, review, retry, and destructive states are accessible and testable. Do not retain current modal markup, focus behavior, tabs, navigation, or class-based visual states as a component library. The replacement needs explicit focus management, keyboard/escape behavior, announcement ownership, and responsive semantics from the approved design contract. |
| Frontend test utilities and E2E seams | **Refactor before reuse** | Tests repeatedly create local `QueryClient` providers and stub `fetch`; examples include `frontend/src/pages/ImportPage.test.tsx:7-14`, `frontend/src/pages/ImportJobDetailPage.test.tsx:7-14`, and `frontend/src/components/MediaImage.test.tsx:7-13`. `frontend/vite.config.ts:39-42` configures only jsdom/Vitest, and `frontend/package.json` has no Playwright/Cypress dependency or browser test script. Existing tests cover auth ordering, API transport, media behavior, imports, navigation, and many page workflows. | Preserve behavior-focused tests and accessible-role queries. Extract shared QueryClient/fetch fixtures and add a browser-level seam for URL/routing, real Clerk lifecycle boundaries, media modes, polling, and auth/cache reset. Do not build visual snapshot coverage before visual design is approved; browser contract tests should assert behavior, not current layout. |

## Contract invariants to carry forward

These are behavioral constraints, not visual implementation recommendations:

1. Clerk owns credentials and sessions. The frontend holds no durable token;
   API and authenticated-media requests obtain a current token through one
   provider.
2. First login calls `POST /me/provision` before the product mounts. The
   backend returns capabilities, not roles, and remains authoritative for
   authorization.
3. Sign-out, unmount, and Clerk identity/session changes clear the token
   provider and auth-scoped query cache before another identity is mounted.
4. Web and mobile consume one owner-scoped API contract. The frontend must not
   create a second authorization or domain-state implementation.
5. Media uses stable `(type, id)` references. Batch access preserves input
   order, permits partial success, refreshes expiring direct grants, and uses
   revocable object URLs for authenticated fetches.
6. Accepted imports remain on the import form and complete through
   notifications. The public detail view polls only active jobs, exposes
   user-safe errors, and permits manual retry only when the backend state and
   attempt limit allow it.
7. Technical import events and payloads stay on the admin-only surface; a
   notification opens the user-safe import detail or recipe detail according to
   its entity type.
8. Design Evidence and prototypes inform decisions but are not production
   dependencies. Production clients implement written contracts with real API
   data, accessibility primitives, and behavior tests.

## Contract gaps requiring follow-up

| Gap | Evidence | Recommended owner and boundary |
| --- | --- | --- |
| Frontend schema generation or drift validation | Manual `frontend/src/api/types.ts`; no generator; generated types explicitly deferred in [`import-pipeline.md`](../import-pipeline.md#current-deferrals). | Frontend/shared-client plus backend OpenAPI workflow. Generate or validate request/response types from the FastAPI schema, define deliberate exceptions for multipart and Blob responses, and fail CI on drift. |
| Stable client error categories and user-safe messages | `ApiError` only carries a free-form code/message/status; import detail maps only a subset of detailed codes; the backend distinguishes high-level and detailed import codes in [`import-error-handling.md`](../import-error-handling.md#terminology). | Shared client, with backend contract input. Define typed HTTP, validation, auth, domain, network, and cancellation categories; keep diagnostic details separate from user copy and retry policy. |
| Query key and lifecycle policy | String keys and invalidations are scattered across pages; auth cache clearing is coupled to `ClerkApplication`. | Frontend/shared-client. Introduce one key factory and policy module for auth scoping, defaults, polling, invalidation, removal, and mutation result handling. |
| Media cache and failure semantics | The stable media contract is implemented, but cache keys preserve input order and tests do not cover batch item errors, expiry refetch, direct-grant expiry, or image-load failure. | Frontend/shared-client. Preserve the backend media contract and harden the hook/image retrieval seam with deterministic tests. |
| Locale, timezone, precision, and copy policy | Page-local `toLocaleString()`/number helpers; no locale provider or translation catalog. | Design/shared contract first, then frontend shared infrastructure. Do not choose a product language or wording from the current prototype/application strings. |
| Browser contract harness | Only jsdom/Vitest is configured; no E2E runner or authenticated browser seam is present. | Frontend/verification plus environment setup. Add behavior-level browser tests for auth/cache reset, URL routing, media retrieval modes, polling, and retry; keep visual assertions design-gated. |

## Candidate child issues that can proceed before visual Design approval

These are bounded follow-up candidates, not issues created by this audit. Each
can be independently verified without selecting the future shell or page
visuals:

1. **Generate frontend API types from the FastAPI OpenAPI contract and enforce
   drift in CI.** Cover camel-case aliases, request/response types, multipart
   exceptions, empty responses, and authenticated Blob responses. Start from
   `backend/app/schemas/` and `frontend/src/api/types.ts`.
2. **Centralize frontend transport and error contracts.** Preserve the current
   token/media boundary while adding typed error categories, safe message
   mapping, malformed-response handling, and tests for network, 401/403,
   404/422, 5xx, and 204 cases. Align import detailed-code handling with the
   backend policy table.
3. **Centralize React Query keys and lifecycle policies.** Define typed keys,
   auth-cache reset behavior, polling intervals, stale-time rules, mutation
   invalidation/removal, and tests for recipe, collection, notification,
   import, admin, and media projections.
4. **Harden the reusable media-access seam.** Preserve `(type, id)`, ordered
   partial results, direct versus authenticated retrieval, expiry refresh, and
   object-URL cleanup while adding canonical cache keys, per-item errors, and
   deterministic expiry/image-failure tests.
5. **Add a behavior-level browser contract harness.** Use stable test fixtures
   to verify authentication bootstrap, cache isolation, URL/deep-link behavior,
   media retrieval modes, import polling/retry, and accessible state changes;
   do not assert the current CSS or visual layout.

The following work is not a pre-design child issue: the replacement shell,
responsive navigation, page composition, modal/tab components, product copy,
locale selection, and visual accessibility treatment require the applicable
approved Design baseline or shared decision first.

## Explicit visual non-reuse boundary

The following are implementation artifacts to inspect for constraints only,
not visual sources for the redesign:

- `frontend/src/styles/app.css` and its class names;
- the `App` header, navigation, toast, and `.layout` composition in
  `frontend/src/app/App.tsx`;
- page JSX and class-based composition under `frontend/src/pages/`;
- the `RecipeGrid` card markup and `PaginationControls` presentation;
- `AdminPage` tab markup and the account-deletion/image modal markup;
- `frontend/src/assets/default-recipe.svg` and other current visual assets;
- any prototype markup, CSS, mock data, or assets under `design/`.

Only the behavior behind these artifacts may be carried forward when it is
listed in the matrix: API calls, typed domain data, auth/cache invariants,
media retrieval, import lifecycle, semantic state requirements, and tests.
The visual system, responsive rules, component boundaries, and interaction
details must come from approved Design Evidence and the written production
contract.

## Evidence index

- [`docs/adr/0001-one-backend-for-web-and-mobile.md`](../adr/0001-one-backend-for-web-and-mobile.md)
  — one backend/API contract for web and mobile.
- [`docs/adr/0002-gateway-identity-backend-authorization.md`](../adr/0002-gateway-identity-backend-authorization.md)
  — gateway identity boundary and backend authorization ownership.
- [`docs/adr/0004-design-baseline-gates-ui-implementation.md`](../adr/0004-design-baseline-gates-ui-implementation.md)
  — Core Design Baseline gate for production UI.
- [`docs/adr/0005-prototypes-are-design-evidence.md`](../adr/0005-prototypes-are-design-evidence.md)
  — prototypes are evidence, not production source.
- [`docs/api.md`](../api.md), [`docs/authentication-and-authorization.md`](../authentication-and-authorization.md),
  [`docs/media-access.md`](../media-access.md), [`docs/import-pipeline.md`](../import-pipeline.md), and
  [`docs/import-error-handling.md`](../import-error-handling.md) — current API and lifecycle contracts.
- `frontend/src/app/`, `frontend/src/api/`, `frontend/src/media/`,
  `frontend/src/components/`, `frontend/src/pages/`, and their adjacent tests
  — current consumers and verification evidence.
