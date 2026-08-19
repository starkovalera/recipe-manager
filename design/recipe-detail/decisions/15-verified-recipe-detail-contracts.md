# Recipe Detail/Edit — Verified Production Contracts

Status: contract audit complete; delivered in [draft PR #80](https://github.com/starkovalera/recipe-manager/pull/80); implementation gaps are tracked as candidate `[DEV]` issues
Task: [#21 — Verify Recipe Detail/Edit contracts](https://github.com/starkovalera/recipe-manager/issues/21)
Updated: 2026-08-19

## Purpose and boundary

This packet records the current production facts that constrain the remaining
Recipe Detail and Recipe Edit Design children. It separates implemented
behavior from missing contracts. It does not choose new product behavior,
design screens, visual treatment, or production implementation.

The packet was verified against `origin/main` at commit
`01538e36fa695b8acf4d1870185a5036d39715d2` before the audit branch was
created. Source links point to the permanent repository files and line ranges
that established each finding.

## Evidence summary

| Contract | Current production fact | State | Design consequence / next contract |
| --- | --- | --- | --- |
| Ingredient Unit | `Ingredient.unit` is nullable free text; schemas and patching do not enforce a dictionary. | Missing | Fixed localized Unit behavior remains Design-only; [#71](https://github.com/starkovalera/recipe-manager/issues/71) blocks the remaining Unit-dependent child. |
| Field and collection limits | Several aggregate limits are implemented, but most field lengths/ranges and recipe-media capacity are not defined. | Partial | Use the verified defaults below; do not invent field limits. [#72](https://github.com/starkovalera/recipe-manager/issues/72) and [#75](https://github.com/starkovalera/recipe-manager/issues/75) are candidates. |
| Ingredient/instruction identity and order | Ingredients have stable IDs and persisted positions; instructions are an ordered JSON list of strings with no stable step IDs. | Partial | Ingredient reorder can be described from current behavior; instruction identity/reorder semantics need [#73](https://github.com/starkovalera/recipe-manager/issues/73). |
| Save and concurrency | Recipe PATCH is one partial request with whole-list replacement for ingredients/instructions and post-commit response; no stale-write token or Recipe conflict contract exists. | Partial | Design one global Save outcome, but do not promise conflict handling until [#74](https://github.com/starkovalera/recipe-manager/issues/74). |
| Media capacity, ownership, lifecycle | Read access, owner scoping, imported-resource states, current-cover protection, and URL-child cascade exist; Recipe-level upload/manage-media capacity does not. | Partial | Read-only Media/Import Info behavior may use current facts; Manage Media remains blocked by [#75](https://github.com/starkovalera/recipe-manager/issues/75). |
| Collection/Tag selectors and pagination | Owner-scoped list endpoints use offset pagination; tags are active-only and stably name-sorted, while collections lack a selector/search contract and a documented tie-breaker. | Partial | Existing list/assignment behavior is factual; selector behavior and Save boundary require [#76](https://github.com/starkovalera/recipe-manager/issues/76). |
| Estimated nutrition | Nullable JSON with four nullable floats; no completeness, units, ranges, provenance, or typed output semantics. | Missing | Nutrition design is blocked by [#77](https://github.com/starkovalera/recipe-manager/issues/77). |
| Authorization | Authenticated FastAPI endpoints enforce current-user ownership; `DEBUG` adds owned debug detail only, and `SUPERADMIN` does not broaden ordinary Recipe access. | Verified | Edit, media, organize, and delete are owner-only in the current V1 contract. Do not infer collaboration or shared ownership. |

## Verified facts by contract

### 1. Unit dictionary and allowed values — missing

The current persistence field is `Ingredient.unit`, a nullable `String`; the
public input and output schemas expose `str | None`, and Recipe patching only
trims the value. There is no Unit enum, alias table, dictionary endpoint, or
invalid-value error in the current Recipe contract.

Evidence: [`Ingredient` model](../../../backend/app/models/__init__.py#L354-L364),
[`IngredientIn`/`IngredientOut`](../../../backend/app/schemas/recipes.py#L26-L48),
and [`_apply_ingredient_fields`](../../../backend/app/services/recipes.py#L54-L63).

The approved Design assumption remains a fixed localized dictionary with
searchable aliases and an explicit `No unit` state. That assumption is not a
production fact. Candidate [#71](https://github.com/starkovalera/recipe-manager/issues/71)
must define canonical wire values, aliases, ordering, localization ownership,
legacy-value handling, and validation across import and manual edit.

### 2. Field and collection limits — partially verified

The current default settings and validation seams establish these limits:

| Area | Current value | Enforcement/evidence |
| --- | ---: | --- |
| Ingredients per Recipe | 50 | `Settings.max_recipe_ingredients`; `validate_recipe_size` |
| Total non-empty instruction text | 1000 characters | `Settings.max_recipe_instruction_chars`; joined with newlines |
| Recipe note | 500 characters | `Settings.max_recipe_note_chars`; trimmed before length check |
| Active Tags per user | 50 | `Settings.max_tags_per_user` on tag creation |
| Import images per job | 10 | `Settings.max_import_images` |
| Import videos per job | 1 | `Settings.max_import_videos` |
| Imported image upload size | 8 MiB | `Settings.max_upload_bytes` |
| Imported video size | 64 MiB | `Settings.max_video_bytes` |
| Generic list page | default 24, maximum 100 | `DEFAULT_PAGE_LIMIT`/`MAX_PAGE_LIMIT` |
| Media access batch | 1–100 references | `MediaAccessRequest.items` |

Evidence: [`Settings`](../../../backend/app/core/config.py#L78-L87),
[`recipe_limits`](../../../backend/app/services/recipe_limits.py#L21-L45),
[`pagination`](../../../backend/app/core/pagination.py#L1-L2),
[`MediaAccessRequest`](../../../backend/app/schemas/media.py#L13-L20), and the
[current API summary](../../../docs/api.md#L28-L43).

The following are not currently bounded by a Recipe schema or validation
contract: Title, Author, Ingredient name, Quantity, Unit, individual
instruction-step length, Collection name/description, numeric Servings and
Cooking time ranges, and Nutrition values. There is also no Recipe-level image
count/byte capacity; the existing upload limits are import limits, not Manage
Media limits. Candidate [#72](https://github.com/starkovalera/recipe-manager/issues/72)
covers field and aggregate validation; candidate
[#75](https://github.com/starkovalera/recipe-manager/issues/75) covers media
capacity.

### 3. Ingredient and instruction identity/order — partially verified

Ingredients have stable UUID-like database IDs and a required integer
`position`. Recipe PATCH accepts an optional ingredient ID, enumerates the
submitted list from zero, preserves IDs that are present, creates rows without
IDs, and deletes omitted existing rows. Duplicate, foreign, or missing IDs are
rejected. This means ingredient reorder is persisted by the submitted array
order and the position field.

Instructions are stored as `list[str]` JSON and PATCH accepts a replacement
list. The service strips empty steps and writes the submitted order, but there
is no stable instruction ID or per-step mutation contract. A positional list
can be reordered today, but an individual step cannot be addressed safely
across edits. Candidate [#73](https://github.com/starkovalera/recipe-manager/issues/73)
must decide whether that positional behavior is sufficient or whether stable
step identity is required.

Evidence: [`Recipe`/`Ingredient` model](../../../backend/app/models/__init__.py#L304-L364),
[`RecipePatchIn`](../../../backend/app/schemas/recipes.py#L234-L247),
[`patch_recipe` implementation](../../../backend/app/services/recipes.py#L102-L134),
and [API regression coverage](../../../backend/tests/api/test_recipes.py#L679-L711).

### 4. Save semantics, optimistic concurrency, and conflicts — partially verified

The current endpoint is `PATCH /recipes/{recipeId}`. Optional scalar fields,
the full instruction list, the full ingredient list, tag IDs, and cover
selection can be submitted in one request. The service validates the current
recipe, applies the patch, refreshes search text and embedding planning,
commits, dispatches any pending embedding outbox message, and returns a fresh
detail response. The current Design rule of one Recipe Edit draft and one
global Save is compatible with this request boundary, but it is not itself an
implemented optimistic-concurrency contract.

`updatedAt` is returned in the detail/list representation, but the PATCH
request has no version, ETag, or `If-Match` precondition. No Recipe-specific
conflict code exists; a stale writer can currently overwrite a newer write.
Candidate [#74](https://github.com/starkovalera/recipe-manager/issues/74)
must define the token, atomic check/update, conflict response, reload/retry
behavior, and the boundary between Recipe Save and immediate resource actions.

Evidence: [`RecipePatchIn`](../../../backend/app/schemas/recipes.py#L234-L247),
[`PATCH` route](../../../backend/app/api/routes/recipes.py#L42-L58),
[`patch_recipe`](../../../backend/app/services/recipes.py#L163-L179), and the
[generic conflict layer](../../../backend/app/core/errors.py#L91-L97).

### 5. Media capacity, ownership, lifecycle, and permissions — partially verified

The current read/access contract uses stable RecipeImage IDs and authenticated
grants. A Recipe image is eligible only when linked to an `ACTIVE` Recipe owned
by the current user. Import source images use the same owner boundary and are
inaccessible after retained artifacts are removed. Public domain responses do
not expose storage keys or durable media URLs.

Imported Recipe Resources have `SOURCE`/`COVER_CANDIDATE` roles,
`USED`/`IGNORED`/`UNKNOWN`/`DELETED` statuses, optional parent/child links, and
positions. Resource status can be changed to `used` or `deleted`; deleting a
current cover is rejected, and deleting a URL resource cascades to non-cover
children. These are current facts for Import Info, not a general media upload
contract.

There is no Recipe-level upload intent, Manage Media mutation endpoint,
Recipe-image capacity, orphan/rollback contract, or explicit media-draft
commit boundary in production. Candidate [#75](https://github.com/starkovalera/recipe-manager/issues/75)
must resolve those gaps before Manage Media is sliced.

Evidence: [`RecipeImage`/`RecipeResource` model](../../../backend/app/models/__init__.py#L375-L410),
[`resource status mutation`](../../../backend/app/services/recipes.py#L209-L240),
[`media access contract`](../../../docs/media-access.md#L18-L66), and
[resource regression coverage](../../../backend/tests/api/test_recipes.py#L788-L893).

### 6. Collection/Tag selectors and pagination — partially verified

`GET /collections` and `GET /tags` are current-user scoped and accept
`limit`/`offset`; the default page limit is 24 and the maximum is 100. Both
return `items`, `total`, `limit`, and `offset`. Active Tags exclude soft-deleted
rows and sort by case-insensitive name plus ID. Collections sort by name but
have no documented tie-breaker. Recipe detail returns assigned Collections and
active Tags. Recipe PATCH accepts active current-user `tagIds`; Collection
membership is changed through separate immediate PUT/DELETE endpoints.

No selector-specific search/filter, stable Collection tie-breaker, large-set
interaction, stale-page behavior, or unified Collection assignment draft
boundary is defined. Candidate [#76](https://github.com/starkovalera/recipe-manager/issues/76)
must define that shared API behavior before platform selector children are
marked ready.

Evidence: [`collection/tag routes`](../../../backend/app/api/routes/collections.py#L14-L76),
[`tag route`](../../../backend/app/api/routes/tags.py#L12-L53),
[`collection queries`](../../../backend/app/collections/queries.py#L16-L45),
[`tag queries`](../../../backend/app/tags/queries.py#L12-L22), and the
[API summary](../../../docs/api.md#L52-L84).

### 7. Incomplete nutrition and validation — missing

`Recipe.nutrition_estimate` is nullable JSON. The input model exposes nullable
`calories`, `proteinGrams`, `fatGrams`, and `carbsGrams` values as floats, but
does not define ranges, units, precision, completeness, provenance, or a typed
output state. The detail response exposes a nullable untyped dictionary. A
missing object and a partial object are therefore not a documented product
state distinction.

Candidate [#77](https://github.com/starkovalera/recipe-manager/issues/77)
must define missing/partial/complete/invalid states, clearing, import/manual
ownership, serialization, and validation. Actual cooking-session nutrition is
still deferred by the current Design scope.

Evidence: [`NutritionEstimateIn` and Recipe detail schema](../../../backend/app/schemas/recipes.py#L43-L48),
[`Recipe.nutrition_estimate`](../../../backend/app/models/__init__.py#L315-L320),
and [the API summary](../../../docs/api.md#L38-L43).

### 8. Authorization boundaries — verified for the current V1 model

All non-health/application-documentation routes are protected by the verified
identity boundary. Ordinary Recipes, media, Collections, Tags, imports, and
search remain owner-scoped for every role. `DEBUG` adds debug resources and
embedding details only to an owned Recipe detail response; `SUPERADMIN`
administration/diagnostics do not grant ordinary cross-user Recipe access.

The current Recipe Detail/Edit actions therefore have this boundary:

| Action | Current authorization |
| --- | --- |
| Read/edit Recipe content | Current Recipe owner only |
| Read Media / Import Info | Current owner and eligible lifecycle state |
| Manage imported resource status | Current Recipe/resource owner; current-cover invariant applies |
| Organize with Tags | Current-user active Tags and owner-scoped Recipe |
| Organize with Collections | Current-user Collection and owner-scoped Recipe |
| Delete Recipe | Current Recipe owner only; deletion is lifecycle-controlled |
| View debug Import/embedding details | `DEBUG` on an owned Recipe only |

No collaborator, shared-ownership, or role-based edit boundary is implemented
or implied. If collaboration becomes a V1 requirement, it needs a separate
contract issue rather than a design assumption.

Evidence: [API authorization boundary](../../../docs/api.md#L176-L183),
[`recipes` routes](../../../backend/app/api/routes/recipes.py#L42-L86),
and [media authorization](../../../docs/media-access.md#L56-L66).

## Adjacent unresolved production contracts

The audit also preserves two existing handoff questions as explicit candidates:

- `Cooking notes` versus the current generic `Recipe.note`, including its
  validation and clearing semantics — [#78](https://github.com/starkovalera/recipe-manager/issues/78).
- Approved Difficulty and Personal rating controls have no model or API
  persistence — [#79](https://github.com/starkovalera/recipe-manager/issues/79).

Cross-domain discrepancies remain owned by [#22](https://github.com/starkovalera/recipe-manager/issues/22): Import Info's approved bulk
`Mark all reviewed` behavior versus the current per-flag PATCH, and the
Design `TikTok` label versus the backend `TT` wire value.

## Platform-child readiness

The audit does not make the remaining platform children agent-ready by itself.
Shared production gaps must be closed or explicitly accepted before a child
turns a design assumption into a final contract.

| Remaining Design child | Responsive Web (V1) | Native Mobile (paired/V2) | Required shared prerequisites |
| --- | --- | --- | --- |
| Basics/Ingredients completion | Blocked | Blocked, non-blocking for V1 | #71, #72, #79; current approved structural evidence remains valid |
| Instructions editing | Blocked | Blocked, non-blocking for V1 | #72, #73 |
| Cooking notes | Blocked | Blocked, non-blocking for V1 | #72, #78 |
| Estimated nutrition | Blocked | Blocked, non-blocking for V1 | #72, #77 |
| Save request/conflict states | Blocked | Blocked, non-blocking for V1 | #72, #74 |
| Manage Media | Blocked | Blocked, non-blocking for V1 | #72, #75 |
| Organize Recipe selectors | Blocked | Blocked, non-blocking for V1 | #76 |
| Existing read-only Detail/Focus/Media/Import Info/delete foundation | Structurally unblocked by this audit; final visual work remains | Paired evidence exists; non-blocking for V1 | Existing approved decisions; #22 still owns cross-domain reconciliation |

The next `[WEB]` and `[MOBILE]` issues should therefore be created as paired
platform slices only after their listed shared prerequisites are closed or
explicitly accepted. The mobile status is intentionally non-blocking for the
V1 Core Design Baseline.

## Verification record

- Production code changed: none.
- Design source-of-truth files inspected: current scope, implementation handoff,
  functional scope, consolidated Edit decisions, shared inventory, API summary,
  and media access contract.
- Current production sources inspected: Recipe models/schemas/routes/services,
  limits/settings, Collection/Tag queries, media authorization, and focused API
  regression tests.
- Candidate gaps recorded: [#71](https://github.com/starkovalera/recipe-manager/issues/71),
  [#72](https://github.com/starkovalera/recipe-manager/issues/72),
  [#73](https://github.com/starkovalera/recipe-manager/issues/73),
  [#74](https://github.com/starkovalera/recipe-manager/issues/74),
  [#75](https://github.com/starkovalera/recipe-manager/issues/75),
  [#76](https://github.com/starkovalera/recipe-manager/issues/76),
  [#77](https://github.com/starkovalera/recipe-manager/issues/77),
  [#78](https://github.com/starkovalera/recipe-manager/issues/78), and
  [#79](https://github.com/starkovalera/recipe-manager/issues/79).
- Cross-domain audit dependency: [#22](https://github.com/starkovalera/recipe-manager/issues/22).
