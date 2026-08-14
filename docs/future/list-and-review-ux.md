# List and Review UX Improvements

Stage: Captured

First-version scope: reconcile with the Core Design Baseline before promotion

## Tags

- Validate tag name and tag description length on both frontend and backend.
- Surface existing backend `DUPLICATE_TAG` and `TAG_LIMIT_EXCEEDED` errors on the Tags page instead of leaving mutation failures invisible.
- Show a persistent recipe-count badge/counter next to each tag. The existing tag-usage endpoint and delete confirmation already expose this count on demand.
- Add a way to navigate from a tag to the list of recipes containing that tag.
- Add tag sorting options.
- Add quick tag search/autocomplete by tag name.
- If `MAX_TAGS_PER_USER` becomes greater than backend `MAX_PAGE_LIMIT`, replace the recipe editor's current `limit=100` tag loading with a searchable/paginated tag picker.

## Ingredients and recipe editing

- Add frontend and backend length limits for ingredient `name`, `quantity`, `unit`, and `note`. Ingredient count and required-name validation already exist.
- Insert a newly added ingredient at the top of the editable ingredient list.
- Add ingredient reordering controls. Ingredient `position` is already persisted from the frontend array order; only the user-facing reordering interaction is missing.
- Add an ingredient calculator that scales quantities by the selected number of servings. The recipe `servings` field already exists in the model and API but is not yet exposed as a scaling workflow.

## Notifications and review flags

- Add distinct colors and icons for different notification types while preserving accessible text/status cues.
- Revisit whether review concerns should use multiple flag types instead of one generic warning type. Define behavior when a recipe has more than one open flag, including aggregation, ordering, independent resolution, list-page indicators, recipe-detail messaging, and mobile/web UI/UX.
- Add bulk review-flag resolution so a user can close multiple or all selected flags in one operation. Apply the changes atomically and evaluate embedding scheduling once from the final flag state instead of once per flag.

## Import history

- Evaluate whether users need a general Import History page in addition to notification history and direct ImportJob detail links. Before implementation, research the expected use cases, retention expectations, filtering/status needs, and retry/navigation UI. The current product intentionally relies on notifications plus per-job detail.
- Handle `ImportJobSource` records without an image storage/media key in the frontend, including the user-facing ImportJob detail page. Do not render a broken media request; show the available source metadata and an explicit unavailable-media fallback when appropriate.

## Pagination and lists

- Finish pagination-aware selectors on recipe detail. The main Recipes, Collections, and Tags pages already have pagination controls, but recipe detail still loads collections without paging controls and loads only the first 100 tags.
- Add sorting and filters for collections on backend and frontend.

## Refinement rule

These opportunities touch active Design Domains. During Core Design Baseline work, either incorporate the behavior into first-version scope or leave it explicitly deferred here. Create Design issues before Development issues whenever interaction or information hierarchy remains unresolved, and preserve accessible error/status behavior in every promoted slice.
