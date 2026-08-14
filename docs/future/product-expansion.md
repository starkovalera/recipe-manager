# Product Expansion

Stage: Captured

First-version scope: excluded unless separately promoted

## Onboarding and account value

- Add mandatory first-login account onboarding for newly provisioned users. Before entering the product, the user must choose exactly one immutable recipe language: English or Russian. Persist the selection in `UserSettings`, prevent later language changes, provide translated English and Russian default-tag sets, and create the matching tags only after the language is selected. Until selection succeeds, the account page is the only accessible product page.
- Add per-user successful-import quotas over a configurable accounting period such as a week or month. Model reusable quota tiers/classes so different users can receive different limits, including an explicit `UNLIMITED` tier; let administrators manage tier definitions or assignments and see each user's quota and current usage; let users see their own quota, accounting period, and actual usage. Define atomic counting under concurrent imports, period boundaries and time zone, tier changes during an active period, and which terminal import statuses consume quota before implementation.

## Recipes and manual content

- Let users rate recipes and optionally attach a comment to each rating. Define the rating scale, whether a user may keep only one current rating per recipe, edit/delete behavior, owner scoping, visibility in shared recipe libraries, and whether aggregate ratings affect sorting or search before implementation.
- Add an editable recipe difficulty assessment. Define a fixed difficulty scale, extend the AI extraction prompt and response schema so imported recipes receive an initial value, persist and expose it through the recipe model/API, and let the user change it when editing the recipe. Backend validation must remain authoritative for both AI-produced and user-provided values.
- Add shared recipe libraries for multiple users. Introduce an explicit shared-space/library entity with membership and role-based access instead of weakening existing owner-scoped queries; define ownership, invitations, read/write permissions, recipe and media lifecycle, collections, tags, search and embeddings visibility, import destinations, member removal, and deletion behavior before implementation.
- Expose shared recipe-editing domain limits through a backend-owned API/capabilities response instead of configuring them independently in the frontend. Replace `VITE_MAX_RECIPE_INGREDIENTS`, `VITE_MAX_RECIPE_INSTRUCTION_CHARS`, and `VITE_MAX_RECIPE_NOTE_CHARS` with values derived from the same backend settings that enforce these limits.
- Let users upload additional images to an existing recipe. Persist each accepted image through the existing `RecipeImage`/`RecipeResource` relationship as a recipe-owned image resource, resize or recompress images that exceed the configured maximum dimensions or byte size, and enforce a backend-owned per-recipe maximum for resources of each applicable type. Define validation, frontend feedback, cover-selection behavior, deletion/storage cleanup, and concurrent-upload handling before implementation.
- Add aligned frontend and backend length limits for every remaining editable recipe field, including title and author name. Ingredient count, instruction length, note length, and required ingredient names are already validated; backend validation remains authoritative.
- Normalize recipe-title formatting and casing using an explicitly defined locale-aware rule without corrupting brands, abbreviations, or proper names.
- Support fully manual recipes and standalone manual notes that can be added to collections alongside imported recipes. Clarify whether notes share a common collection-item abstraction with recipes or remain a separate entity.

## Authors

- Replace the free-form `Recipe.author_name` field with an owner-scoped `Author` entity. Store at least `owner_id` and `name`, enforce uniqueness of the normalized name within an owner, and support one or more optional author links. Relate recipes to authors through an explicit recipe-author association.
- During import, resolve a parsed author name against the importing user's existing authors and create a new author only when no match exists. Define normalization carefully so casing or harmless whitespace does not create duplicates while genuinely different authors remain distinct.
- In recipe editing, let the user select an existing author from a dropdown/search autocomplete or enter a new name. A new name creates an owner-scoped author and links it to the recipe as part of the save workflow.
- Add an Authors page with search/list navigation and an author detail page showing editable name, editable links, and linked recipes.
- Support merging multiple authors into one canonical author while preserving every recipe association and resolving duplicate links safely. The merge must be transactional, owner-scoped, and explicit about which author record survives.

## Refinement rule

Treat each opportunity as its own Future Capability before promotion. Resolve ownership, visibility, lifecycle, permissions, migration, search/indexing effects, web/mobile journeys, and API boundaries before generating issues. Coordinate imported author-link behavior with [`import-and-ai.md`](import-and-ai.md) so the same capability is not refined twice.
