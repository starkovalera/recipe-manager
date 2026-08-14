# Search Evolution

Stage: Captured

First-version scope: excluded unless separately promoted

## Query interaction and explainability

- Support multiple simultaneous search chips, including repeated chips of the same filter type. Define backend request representation, AND/OR semantics within and across chip types, duplicate handling, URL/state serialization, autocomplete behavior, removable-chip UI, Search Debug explanations, and stable pagination when the active chip set changes.
- Improve autocomplete for structural concepts: when the user enters text similar to an existing tag such as `низкокалорийное`, `быстрое`, `высокобелковое`, or `без сахара`, explicitly offer the corresponding tag chip. Do not silently convert free text into a tag filter.
- On Search Debug, show how the query was processed: structured filters only, semantic-only text, or mixed chips plus semantic text. For semantic-only queries, explain that numeric and structural filters were not applied.
- Add pagination controls to Search Debug; it currently uses `limit=20` and `offset=0`.
- When autocomplete suggests one concrete recipe, selecting that recipe chip should navigate directly to recipe detail instead of adding a search filter.

## Embedding input and derived semantics

- Add deterministic derived semantic labels to embedding input from structured fields without writing them to `recipe_tags`: for example `быстрое`/`quick` from `cook_time_minutes`, `низкокалорийное` from calories, and `высокобелковое` from protein grams. Do not generate these labels through AI at search time.
- Introduce a version for embedding-input rules, for example `EMBEDDING_INPUT_VERSION = "v2"`, and include it in the input hash or input text. When derived-label rules change, recompute embeddings.
- When derived labels are added, update invalidation/recompute rules for title, `ingredients.search_name`, instructions, `nutrition_estimate`, `cook_time_minutes`, and the derived-label rule version.
- Investigate semantically close ingredient terms such as `сахарозаменитель` and `подсластитель`: evaluate whether current vector search handles them adequately before adding synonym normalization or query expansion.

## Structured filters, suggestions, and ranking

- Later consider strict numeric filters: `maxCookTimeMinutes`, `maxCalories`, `minProteinGrams`, and `maxCarbsGrams`. Do not implement them before the UX decision.
- Before an AI query parser, add lightweight query-concept suggestions: for example `быстро` → the `быстрое` tag or a future `до 20 минут` filter; `низкокалорийное` → a tag or a future calorie filter.
- Before tuning ranking, collect a small manual evaluation set with a query, expected good recipe IDs, and expected bad recipe IDs.
- Leave query expansion and hybrid-ranking boosts for a later stage after Search Debug, embedding-input preview, derived labels, and the evaluation set.
- A possible future hybrid score is semantic similarity + title-match boost + ingredient-query boost + tag-match boost + derived-property boost + recency/favorite boost. Do not add it before the baseline semantic behavior is understood.

## Promotion boundary

Approve query/chip interaction semantics and build the evaluation set before ranking changes. Any promoted implementation must preserve owner scoping, stable pagination, explainability, embedding invalidation, and deterministic tests.
