# API, Schema, and Platform Constraints

Status: verified technical-constraint input for issue #22; delivered in
[merged PR #82](https://github.com/starkovalera/recipe-manager/pull/82).
Proposed changes are not implemented.

Task: [#22 — Audit API, schema, and platform constraints](https://github.com/starkovalera/recipe-manager/issues/22)

Updated: 2026-08-19

## Outcome and boundary

This document is the shared technical handoff for the Core Design Domains. It
records what the current runtime can do, what a client may safely rely on, and
what is still ambiguous or contradictory. It is not a screen specification,
visual baseline, API implementation plan, or approval of any proposed
Development work.

The audit covers:

- authentication, provisioning, ownership, roles, and account lifecycle;
- Recipes, library/search, Recipe Detail/Edit, review, and media references;
- import submission, durable job processing, retry, notifications, and
  terminal states;
- Collections, Tags, membership, and organization limits;
- notifications, unread/read behavior, history, and deep links;
- Profile/account and the operational boundary;
- shared web/mobile transport, error, pagination, media, and platform
  constraints.

No files under frontend, backend, infra, or docker are changed by this
deliverable. A proposed change below is an input for a future issue, not a
current capability.

## How to read the findings

| Label | Meaning |
| --- | --- |
| Current | Verified in the active route, schema, model, service, or current technical document. |
| Ambiguous or contradictory | A client or Design child must not invent behavior until the named decision or contract is resolved. |
| Proposed Development change | A bounded follow-up candidate with affected consumers and a verification seam. It is not implemented by #22. |
| Deferred | Explicitly outside the V1 Core contract or reserved for the post-V1 V2 mobile sequence. |

The runtime route and schema sources are authoritative for implemented
behavior. The hand-maintained [API documentation](../../docs/api.md) remains a
useful integration index, but it is not treated as authoritative where it
differs from the active runtime. The [frontend contract
audit](../../docs/architecture/frontend-contract-audit.md) is the current
evidence for web-client reuse and type drift; it does not redefine the
backend contract.

## Evidence and source order

The audit follows the repository's Design source order:

1. [Product Design Roadmap](../roadmap.md) and
   [#20 scope and decision inventory](scope-and-decision-inventory.md);
2. [CONTEXT.md](../../CONTEXT.md) and
   [shared product scope](product-scope.md);
3. active technical contracts:
   [API documentation](../../docs/api.md),
   [authentication and authorization](../../docs/authentication-and-authorization.md),
   [media access](../../docs/media-access.md),
   [import pipeline](../../docs/import-pipeline.md),
   [import error handling](../../docs/import-error-handling.md), and
   [production architecture](../../docs/architecture/production-architecture.md);
4. active runtime routes, schemas, models, services, and configuration under
   [backend](../../backend/);
5. [frontend contract audit](../../docs/architecture/frontend-contract-audit.md)
   and the deferred
   [native-client decision packet](../../docs/architecture/native-client-decision-packet.md);
6. historical plans and prototypes only as process evidence, never as a
   current contract.

The static source audit was performed against the fresh branch base
01538e36fa695b8acf4d1870185a5036d39715d2 on 2026-08-19. Runtime-dependent
behavior remains assigned a concrete verification seam in the candidate table
below.

## Shared cross-client contract matrix

| Contract area | Current capability and invariant | Shared web/mobile implication | Gap or verification seam |
| --- | --- | --- | --- |
| API boundary and serialization | One owner-scoped HTTPS API crosses KrakenD into FastAPI. FastAPI schemas use camelCase aliases at the HTTP boundary. The runtime exposes JSON endpoints plus multipart import and binary/local-media retrieval. | A future mobile client consumes the same API and server authority; it must not create a second backend or bypass the gateway/backend authorization boundary. | Runtime OpenAPI should become the canonical generated or validated client source. Verify method/path parity, aliases, status codes, multipart, binary, and 204 responses against gateway configuration and frontend wrappers. |
| Identity and ownership | Clerk owns credentials, sessions, invitation delivery, and the external subject. KrakenD validates the token and injects the trusted subject. FastAPI resolves the internal User, lifecycle status, roles, capabilities, and owner scope. | Token acquisition and storage are platform adapters; user provisioning, authorization, and data ownership are shared server contracts. Capabilities are UX hints, never a security decision. | Keep the Clerk-versus-Recipe-Manager account boundary explicit. Verify missing identity, unprovisioned identity, deactivated user, deletion-pending user, ordinary owner access, and internal role access. |
| Success and error envelopes | Successful routes use 200, 201, 202, or 204 according to the route. Application errors use an ApiError envelope with errorCode, message, and optional extra data; typed classes cover 400, 401, 403, 404, 409, 500, 502, and 503 cases. FastAPI's default request-validation response remains a separate 422 shape because no RequestValidationError handler is installed. | Clients need one safe parser with unknown-code and non-JSON/network fallbacks. User copy and retry behavior must be based on stable categories, not arbitrary messages. | Proposed C2 below: publish a typed public error/validation contract and retry classification. Verify representative malformed JSON, missing auth, forbidden access, not found, conflict, provider failure, and 422 cases through the API boundary. |
| IDs, deduplication, and concurrency | Domain IDs are opaque UUID-like strings. Import creation deduplicates by owner plus Idempotency-Key or clientImportId and returns 202 for new work or 200 for an existing job. Recipe editing has no ETag, version, conditional request, or optimistic-conflict response contract. | Do not promise cross-client conflict resolution, offline write merging, or client-generated durable IDs beyond the import idempotency inputs. | Verify duplicate submissions, concurrent claims, owner isolation, and retry behavior. Decide whether recipe saves need a version/ETag contract before a Design child specifies conflict UI. |
| Pagination and list density | Recipes, Collections, Tags, and search accept limit 1–100 with a default of 24 and offset from 0. Recipe/search responses expose total or hasMore as applicable. Notifications are currently an unbounded owner-scoped list. Collection detail embeds all active recipes without a nested pagination contract. Imports have no owner-scoped list endpoint. | Shared product meaning includes empty, sparse, dense, and loading states, but each platform may choose different controls and navigation. A client must not assume every domain has the same pagination shape. | Verify boundary values, stable ordering, offset behavior, and owner scope. Decide whether notification history, Collection detail, or active-import recovery requires cursor pagination or a list endpoint before design promises those flows. |
| Media references and retrieval | Public clients receive stable media references, not storage keys. POST /media/access accepts 1–100 references and returns ordered per-item grant or indistinguishable error. Grants are direct with expiry or authenticated_fetch; local media uses a stable authenticated route. | Web uses browser File/Blob/object-URL adapters; mobile will need native file/URI/cache adapters. Both must refresh expiring grants, preserve partial results, and avoid durable storage-key assumptions. | There is no general recipe-image upload or upload-intent/resumable-upload contract. Keep Manage Media upload deferred unless explicitly promoted. Verify owner scope, deleted import artifacts, grant expiry, partial failure, object-URL/file cleanup, and direct versus authenticated retrieval. |
| Asynchronous work | Imports are queue-first with transactional outbox and durable ImportJob state. Embeddings, account deletion, and maintenance also cross worker/provider boundaries. The server owns execution; clients observe durable state and notifications. | A client may poll or refresh on resume but must never treat a client process as the worker. Background execution, push, offline writes, and resumable uploads are not current shared contracts. | Verify atomic QUEUED-to-RUNNING claim, attempt counting, outbox recovery, stale-job cleanup, terminal notifications, and provider failure classification. Import cancellation is not currently exposed. |
| Production versus preview topology | PROD requires PostgreSQL, SQS, and S3; preview/dev defaults may use PostgreSQL plus Dramatiq/local storage. The transport and domain contract is intended to be the same across environments. | Clients consume HTTPS/API/media behavior and must not depend on Redis, Dramatiq, local paths, bucket names, or queue details. | The authentication document contains an older non-production topology diagram. Use the production architecture and current config as the source for topology; verify preview/prod endpoint and media behavior separately. |

## Core Design Domain matrix

| Core Design Domain | Current API/schema contract | User-visible state to backend state mapping | Shared versus platform-specific boundary | Open contract and verification seam |
| --- | --- | --- | --- | --- |
| Authentication, invitations, and onboarding | Clerk session/invitation flows are external; POST /me/provision is idempotent at the product boundary and returns 201 for a new User or 200 for an existing one; GET /me returns id, email, and backend-derived features. Protected routes resolve the trusted subject and enforce User status and owner/role checks. | No session or invalid trusted identity maps to an unauthenticated/error entry state. Valid subject without a local user maps to provisioning-required. ACTIVE maps to usable product access. DEACTIVATED and DELETION_PENDING map to blocked access. POST /me/deletion returns 202 and moves the account into deletion-pending processing. | Shared: Clerk subject boundary, provisioning, status, roles, capabilities, owner authorization, and safe errors. Web: browser Clerk session and gateway/CORS. Mobile: deferred native Clerk/session adapter, secure storage, and deep links. | First-login/onboarding scope and the Clerk-versus-app account UI boundary are unresolved. Verify 401/403/409 behavior, sign-in/session change cache clearing, provisioning races, webhook idempotency, and owner isolation. |
| Recipes, library, detail, edit, search, and review | GET /recipes is paginated with tag, ingredientQuery, sourceName, authorName, and title filters. POST /search supports text plus structured chips and returns hasMore; suggestions are bounded. Detail exposes sourceName, title/note, servings, cookTimeMinutes, nutritionEstimate, authorName, instructions, ordered ingredients, tags, Collections, resources/sources, images/coverOptions, reviewFlags, and debug data only for eligible internal access. PATCH supports the current RecipePatch fields; DELETE marks deletion pending and returns 204; per-flag review and resource status patches exist; embedding retry exists. | ACTIVE recipes are list/detail readable. Empty, loading, error, permission, long-content, and dense states are client states over owner-scoped queries. Review flags are open or resolved; embedding is asynchronous and has stale/running/ready/failed/skipped-due-to-flags states. Recipe deletion is a backend DELETION_PENDING lifecycle, not a normal editable state. | Shared: field meaning, ordering identity, validation, search filters, review/resource/media references, owner scope, and save/error semantics. Web: responsive editing, browser media retrieval, keyboard and focus behavior. Mobile: later native navigation/keyboard/media behavior, without a second data model. | D1 documents a narrower Recipe PATCH than runtime. Difficulty/rating, Cooking notes versus Recipe.note, review bulk versus per-flag resolution, TikTok versus TT, media upload, numeric limits, null-clearing, and optimistic concurrency remain open. Verify route/schema/docs parity and write contract tests before Recipe children promise these behaviors; #21 remains the Recipe-specific input. |
| Imports and asynchronous processing | POST /imports is multipart with clientImportId, optional text/url/files, X-Client-Id, and Idempotency-Key. Current validation is text up to 1000 characters, up to 10 JPEG/PNG/WebP images, and 8 MiB per image. A new job returns 202; an idempotent duplicate returns 200. GET /imports/{jobId} returns status, attempts, source metadata, error fields, and created recipe id when available. Retry returns 202 for FAILED jobs below the three-attempt default. | queued means accepted/not yet claimed; running means server processing; succeeded means a Recipe was created; succeeded_with_flags means a Recipe exists with review work; failed means a terminal or retryable failure according to attempts/error policy; failed_artifacts_removed means failed source artifacts are no longer available. CANCELLED exists in the model enum but has no current route/transition. | Shared: source types, idempotency, owner scope, job state machine, retryability, safe errors, notification/deep-link semantics. Web: FormData/File submission, form clears after acceptance, detail polling while queued/running at 1 second, notification polling at 5 seconds. Mobile V2: native file URI conversion, foreground/app-resume refresh, no push/offline/background execution contract. | D2 is a public/runtime state contradiction: failed_artifacts_removed is missing from docs, source statuses pending/uploading/validating/failed are reserved, and cancellation is unreachable. The configured name max_parallel_imports_per_client is enforced by an owner-wide queued/running count, not per client_id. Verify transitions, retries, cleanup, multi-client concurrency, and public status/error serialization; see C3/C4. |
| Collections and Tags | Collections: paginated list, create, detail, delete, and PUT/DELETE membership. Detail embeds all active recipe list items. No Collection PATCH route exists although description is stored. Tags: paginated active list, create, patch, usage, and soft delete; active tags are capped at 50 and duplicate names are normalized case-insensitively. | Collections have no server draft lifecycle; clients render empty/sparse/dense/loading/error and membership mutation states. Tags are active or soft-deleted; deleted tags are excluded from active list and usage. Missing collection/recipe membership operations produce owner-scoped not-found behavior, while removing a non-member is currently a no-op. | Shared: owner scope, identity, tag normalization/capacity, membership meaning, list limits, and error semantics. Web: selectors, menus, dense tables/lists, and responsive organization. Mobile: native sheets/selectors and navigation are paired V2 behavior, not a second API. | D12 remains unresolved: Collection description editing, duplicate/conflict semantics, membership error codes, selectors for large sets, and nested detail pagination have no shared Design contract. Verify explicit response/error behavior and load-size limits before creating a Development child; collection update/history pagination are conditional candidates. |
| Notifications and activity | GET /notifications returns all owner notifications newest-first. Current types are import started/failed/succeeded/succeeded_with_flags. PATCH changes read/unread; PATCH /notifications/read-all reads through a client-snapshot notification id. Items may deep-link to a Recipe or Import Job and include structured data. There is no remote push/device-token contract. | unread/read is the current persisted presentation state. Import job status remains the source of truth for progress and terminal details; notifications are activity signals and navigation targets, not a replacement for job detail. A missing target must be handled as a stale/deleted destination, not as proof that the notification was invalid. | Shared: event meaning, read-through semantics, entity references, safe data, and owner scope. Web: 5-second foreground polling and browser navigation/toasts. Mobile V2: foreground refresh/app-resume; push permission, APNs/FCM, delivery, and OS notification channels remain platform/deferred work. | History is unbounded and has no cursor/limit; Notification.status is a string on output; data has no per-type public schema. Verify read-all snapshot behavior, ordering, stale deep links, dense history, and network failure. Add pagination only if the approved Core history contract requires it. |
| Profile, account, and operational boundary | GET /me exposes only id, email, and features; Clerk owns provider-managed identity/session actions. Account deletion is an accepted 202 transition into DELETION_PENDING with durable asynchronous processing; the last active superadmin cannot be deleted/deactivated. Internal access/invitation/debug routes are role-gated and belong to the Operational Surfaces Addendum, not Core profile UI. | ACTIVE is usable; DEACTIVATED and DELETION_PENDING are blocked by normal user dependencies; deletion accepted is a pending lifecycle with eventual removal. Role/capability visibility may expose an entry point but never grants access. | Shared: account status, deletion semantics, provider boundary, capabilities, and secure cache/session reset. Web: browser account/settings handoff and operational addendum. Mobile V2: native session restoration, sign-out, deep links, and platform account presentation. | Profile fields, preferences, language onboarding, and the exact Clerk/app settings split are not a current contract. Verify deletion idempotency/recovery, queue failure/reconciliation, last-superadmin protection, and status exposure before promising account screens. Admin/debug remains a separate gate. |

## Evidence path index by Core Design Domain

| Domain | Primary current sources |
| --- | --- |
| Authentication, invitations, and onboarding | [authentication and authorization](../../docs/authentication-and-authorization.md), [users routes](../../backend/app/api/routes/users.py), [auth dependencies](../../backend/app/api/deps.py), [access rules](../../backend/app/access/rules.py), and [KrakenD boundary](../../infra/krakend/README.md) |
| Recipes, library, detail, edit, search, and review | [API documentation](../../docs/api.md), [recipe routes](../../backend/app/api/routes/recipes.py), [recipe schemas](../../backend/app/schemas/recipes.py), [recipe service](../../backend/app/services/recipes.py), [search service](../../backend/app/services/search.py), and [media access](../../docs/media-access.md) |
| Imports and asynchronous processing | [import routes](../../backend/app/api/routes/imports.py), [import models](../../backend/app/models/__init__.py), [request validation](../../backend/app/imports/request_validation.py), [create/retry services](../../backend/app/imports/jobs/create.py), [worker processing](../../backend/app/imports/jobs/process.py), [import pipeline](../../docs/import-pipeline.md), and [error policy](../../docs/import-error-handling.md) |
| Collections and Tags | [Collection routes](../../backend/app/api/routes/collections.py), [Tag routes](../../backend/app/api/routes/tags.py), [Collection schemas/service](../../backend/app/schemas/collections.py), [Collection service](../../backend/app/services/collections.py), [Tag service](../../backend/app/services/tags.py), and [API documentation](../../docs/api.md) |
| Notifications and activity | [notification routes](../../backend/app/api/routes/notifications.py), [notification queries](../../backend/app/notifications/queries.py), [notification schemas](../../backend/app/schemas/notifications.py), [web polling](../../frontend/src/app/App.tsx), [import-detail polling](../../frontend/src/pages/ImportJobDetailPage.tsx), and [API documentation](../../docs/api.md) |
| Profile, account, and operational boundary | [users routes](../../backend/app/api/routes/users.py), [account deletion](../../backend/app/users/deletion.py), [authentication and authorization](../../docs/authentication-and-authorization.md), [access routes](../../backend/app/api/routes/access.py), [invitations routes](../../backend/app/api/routes/invitations.py), and [production architecture](../../docs/architecture/production-architecture.md) |

## Domain-specific constraints and known contradictions

### Authentication and account

Current application authorization is intentionally layered:

- Clerk authenticates the external identity; KrakenD validates the JWT and
  replaces the browser-controlled identity header with a trusted subject.
- FastAPI maps that subject to an internal User and rejects missing,
  deactivated, or deletion-pending users through the normal dependency.
- DEBUG and SUPERADMIN roles affect internal diagnostics and administration.
  Ordinary Recipes, media, imports, notifications, search, Collections, and
  Tags remain owner-scoped for every role.
- GET /me features such as admin-page visibility are presentation hints. They
  are not authorization.

The Design handoff must therefore distinguish no session, signed in but not
provisioned, active, deactivated, and deletion pending. It must not invent
password, JWT, Clerk ticket, or application-session storage in the Recipe
Manager database.

The unresolved onboarding question from #20 is still a product gate: Core may
cover invitation, authentication, provisioning, recovery, and account
lifecycle while mandatory first-login language selection remains deferred, or
the owner may explicitly promote that capability. No API change is implied by
the word onboarding in the roadmap.

### Recipes and search

The runtime contract is broader than the current hand-maintained API index:

- Recipe detail and PATCH include servings, cook time, nutrition estimate,
  ingredients, source/author, tags, note, instructions, cover selection, and
  resource status; DELETE and embedding retry routes also exist.
- Ingredients are ordered by position. A PATCH with ingredients is a
  replacement-style write; supplied ingredient ids must belong to the recipe.
- Recipe and search lists are owner-scoped and bounded by the shared 24/100
  offset pagination rules. Search uses the current embedding only when it is
  ready; structured filters remain authoritative.
- The visible media contract is selection and retrieval of existing images.
  There is no general recipe-image upload or resumable upload intent.
- Review flags currently have per-flag open/resolved PATCH behavior. Open flags
  influence embedding planning and the detail/list hasOpenReviewFlags
  projection.

The #21 audit is complete, but the following cannot be represented as current
capabilities until the named human decisions resolve them:

- difficulty and personal rating persistence;
- whether Cooking notes is the existing Recipe.note or a new field;
- whether a bulk review action, per-flag action, or both are Core;
- whether Manage Media upload/capacity is promoted from Future Capability;
- display label TikTok versus wire enum value TT;
- numeric limits and clear/null semantics for servings, cook time, nutrition,
  and note;
- optimistic concurrency or conflict handling for two clients editing a
  recipe.

### Imports and durable background jobs

The accepted-submission boundary is intentionally separate from the processing
boundary. The form may submit a job and clear immediately; the worker owns
processing and notifications; the user-safe detail owns progress, terminal
outcome, and retry. Internal event history is not a public design contract.

Current limits and error categories are split across request validation and
the import policy:

- synchronous request rejection covers no sources, text length, image count,
  MIME/decoded-image validity, and per-image size;
- processing errors are persisted as high-level import error codes with
  stable detailed policy codes;
- retry is manual and limited to FAILED jobs while attempts remain;
- stale jobs and failed artifacts are reconciled by maintenance;
- a failed job that reaches artifact cleanup becomes
  failed_artifacts_removed and is not retryable.

The public contract must explicitly say which persisted states can be emitted
by GET /imports/{jobId}, which are user-visible, and which are internal or
reserved. At present cancelled is a model value without a current public
transition, and source-level statuses are stored but not exposed in the public
source schema.

### Collections, Tags, and organization

The API supports basic owner-scoped organization, but it does not yet define a
complete organization experience:

- Collection list is paginated, while Collection detail returns an unbounded
  nested recipe list.
- Collection description is stored but cannot be updated through a route.
- Tag capacity is 50 active tags per owner; names are trimmed and normalized
  case-insensitively for duplicate detection; name and description maximum
  lengths are not declared in the input schema.
- Adding membership verifies both owner-scoped entities. Removing a missing
  member currently succeeds as a no-op.

Selectors, search within large tag/Collection sets, update semantics,
duplicate conflict presentation, and membership error copy belong in the
shared Collections contract before platform-specific design slices.

### Notifications

Notifications are an in-app activity projection:

- they are owner-scoped and ordered newest-first;
- read-through uses a notification id from the current client snapshot, so it
  does not accidentally mark newer records read;
- they target a Recipe or Import Job, but do not replace either entity's
  lifecycle endpoint;
- the current web implementation polls every five seconds;
- remote push, device registration, delivery state, and OS notification
  permissions are not implemented contracts.

An approved dense-history experience may require cursor pagination, bounded
payloads, or an incremental change feed. Those are not assumed by this audit.

## Shared versus platform-specific handoff

### Shared/server-owned invariants

The following may be shared by the V1 web client and a later V2 native client:

- one HTTPS API, one owner-scoped authorization model, and no client bypass;
- camelCase HTTP schemas with stable opaque ids and explicit enum values;
- a typed error envelope with safe fallback for unknown/provider/network
  failures;
- pagination and ordering semantics where an endpoint declares them;
- import idempotency, state transitions, attempt/retry rules, and notification
  entity mapping;
- stable media reference and grant semantics, expiry, partial results, and
  cleanup;
- server-authoritative feature/capability values;
- contract fixtures covering route parity, ownership, lifecycle, and errors.

### Web-owned behavior

The current V1 web client may own browser-specific mechanics:

- Clerk React session/token provider and in-memory token lifecycle;
- KrakenD local CORS/Vite origins;
- browser FormData/File construction for multipart imports;
- direct image URLs versus authenticated Blob fetches and object-URL revocation;
- 5-second notification polling and 1-second active import-detail polling;
- responsive navigation, keyboard/focus behavior, and web accessibility
  semantics.

The existing production UI and its CSS are not a visual baseline for the
Design track. The behavior may be reused as evidence only.

### Mobile-owned and deferred behavior

The native client is a V2 planning input, not a V1 implementation commitment.
The same API can be consumed through a native Clerk/session adapter, secure
storage, deep links, native file pickers, native media caching, foreground
polling, and app-resume refresh. Navigation, gestures, sheets, keyboard,
VoiceOver/TalkBack semantics, OS permission prompts, push delivery, background
execution, and offline/resumable writes remain platform-owned or explicitly
deferred. No mobile-specific backend fork is authorized by #22.

## Candidate Development issues and verification seams

These candidates are the change list requested by issue #22. They are scoped
to confirmed contract gaps or are explicitly marked conditional. Human/product
decisions must precede a Development issue when the missing contract changes
product meaning.

| Candidate | Status | Contract gap and affected consumers | Verification seam |
| --- | --- | --- | --- |
| C1. Canonical API/schema source and drift enforcement | Confirmed | Runtime routes/schemas, docs/api.md, and manual frontend types already disagree on Recipe PATCH fields, resource fields, and import terminal status. Affects every Design child, frontend wrappers, future mobile types, and gateway parity. This extends the related direction in #24 rather than creating a competing frontend-only source. | Generate or validate clients from FastAPI OpenAPI; compare route/method/alias/status snapshots with KrakenD; compile frontend consumers; add compatibility fixtures for JSON, multipart, binary, and 204 endpoints. Existing seams: [KrakenD config test](../../backend/tests/infra/test_krakend_config.py) and [frontend client tests](../../frontend/src/api/client.test.ts). |
| C2. Stable public error and validation contract | Confirmed | Application ApiError and default FastAPI 422 responses have different shapes; frontend error codes are unrestricted strings and do not carry stable field-level or retry metadata. Affects all domain error/loading/retry states and both clients. | API integration matrix for 400/401/403/404/409/422/5xx; normalize malformed/non-JSON/network failures; assert safe messages, stable codes, field paths, and retry classification without exposing provider details. Existing seams: [backend error tests](../../backend/tests/api/test_errors.py) and [frontend client tests](../../frontend/src/api/client.test.ts). |
| C3. Public ImportJob lifecycle and terminal-state contract | Confirmed plus human cancellation decision | failed_artifacts_removed is persisted and reachable through maintenance but omitted from docs; cancelled is modeled but has no current transition; source-level lifecycle is reserved and not public. Affects Imports, Notifications, Recipe Import Info, retry UI, and both clients. | State-machine tests for every public transition, serialization/OpenAPI enum, retry eligibility, artifact cleanup, notification mapping, and stale recovery. Existing seams: [terminal-status tests](../../backend/tests/imports/test_terminal_status.py) and [import job API tests](../../backend/tests/api/test_imports_jobs.py). Before adding cancellation, approve its user/product semantics; otherwise document it as internal/unreachable. |
| C4. Import concurrency scope contract | Confirmed | The setting is named max_parallel_imports_per_client, but creation/retry enforce the active queued/running count per owner, not per client_id. Multi-tab, multi-device, and future mobile submissions can observe a different bound than the name implies. | Rename or change behavior intentionally; add concurrent owner/multi-client integration tests, idempotency tests, and race evidence for the active-import limit. Existing [import job tests](../../backend/tests/api/test_imports_jobs.py) cover the owner-wide behavior; a true multi-transaction claim/concurrency seam remains needed. |
| C5. Notification history pagination or incremental-read contract | Conditional on Core history density | GET /notifications is unbounded and has no cursor/limit, while the Core journey explicitly includes notification history. Affects notification list, unread badge, deep links, and future mobile resume. | First approve the V1 history scope and density requirement. If promoted, add bounded cursor/ordering/read-through tests and a contract for stale targets; do not make push a prerequisite. Existing seam: [notification API tests](../../backend/tests/api/test_notifications.py). |
| C6. Collections organization API completion | Conditional on shared Design decision | Collection PATCH/description editing, nested detail pagination, duplicate conflict semantics, and domain-specific membership errors are not defined. Affects organization selectors, Recipe Edit, collection detail, and both clients. | Approve the shared organization contract first; then add explicit PATCH/conflict/error/pagination routes and owner-scoped integration tests only for the promoted behavior. Existing seams: [Collection API tests](../../backend/tests/api/test_collections.py) and [Tag API tests](../../backend/tests/api/test_tags.py). |

The following are not automatic Development issues from this audit:

- Recipe edit limits, null-clearing, optimistic concurrency, Cooking notes,
  difficulty/rating, review resolution, and media upload: #21 and the human
  decision packets must establish product meaning first.
- Remote push, offline writes, resumable/background uploads, and native
  notification delivery: deferred V2 capabilities requiring a separate
  promotion decision.
- Admin/debug/operational screens: separate Addendum scope, even though their
  routes are included in the backend evidence.

## Design handoff references

- [#20 scope and decision inventory](scope-and-decision-inventory.md) is
  updated by this packet's findings: D1, D2, D3, D6, D7, D10, and D12 remain
  explicit rather than silently resolved; this document supplies their current
  runtime evidence and separates product gates from Development gaps.
- [#21 Recipe Detail/Edit contract issue](https://github.com/starkovalera/recipe-manager/issues/21)
  consumes the Recipes section for limits, ordering, review, media, and
  concurrency. It still owns the product decisions that #22 cannot infer.
- [#24 frontend contract audit](../../docs/architecture/frontend-contract-audit.md)
  remains the source for reusable web transport/query/media seams and its
  follow-up issue candidates. C1 and C2 should be coordinated with that work,
  not duplicated as an unowned frontend-only contract.
- [#27 native client architecture input](https://github.com/starkovalera/recipe-manager/issues/27)
  and the [native-client decision packet](../../docs/architecture/native-client-decision-packet.md)
  remain V2/deferred. They inform platform separation but do not authorize
  mobile Development.

## Completion check

Issue #22 is complete for the Design handoff when:

- all six Core Design Domains have a current contract/constraint row;
- user-visible states are mapped to backend lifecycle states;
- permissions, validation limits, pagination, concurrency, media, and failure
  boundaries are explicit;
- current capability is separated from ambiguity, proposed change, and
  deferral;
- each confirmed or conditional candidate names affected consumers and a
  verification seam; and
- no production application code is changed.
