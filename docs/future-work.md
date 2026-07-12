# Future Work and Cleanup Notes

This document tracks known follow-up work, shortcuts, compatibility leftovers, and intentional deferrals that should not be forgotten after phase/subphase completion.

After each completed phase or subphase, review the finished work and propose candidate items to add here before moving on.

## AI and Import Pipeline

- Remove `sourcePosition` and `crop` from the Pydantic AI response schema for `coverCandidate`. They are currently kept as `None`-only legacy compatibility fields after the OpenAI response schema was narrowed to `sourceRef` and `confidence`.
- Consider generated covers: when extraction cannot select a sufficiently convincing source image, generate a cover image from the extracted recipe. Define quality thresholds, cost controls, user visibility, storage lifecycle, and provenance before implementation.
- Align the extraction prompt with configured ingredient-count and instruction-length limits. Any prompt change still requires explicit review and approval, and backend validation remains authoritative.
- Consider extracting additional recipe recommendations into `Recipe.note`. This requires an explicitly approved prompt change, AI output-schema migration, and rules for distinguishing source-authored recommendations from generated content.
- Preserve an author profile URL when `author_name` is derived from a supported platform URL. Build it from the platform's canonical profile prefix and account name, expose it separately from the display name, and render it as a link on recipe detail. Manually entered names without a URL remain plain text.
- Add Telegram import support after defining supported Telegram URL/content types and access constraints.
- Verify and harden import behavior for Instagram Reels and YouTube Shorts, including captions, images/posters, video download, and transcript behavior.

## Background Processing

- Add a transactional outbox for embedding scheduling so persisted embedding lifecycle state and broker publishing are durably coordinated. Publishing is currently best-effort and intentionally secondary to completed user operations.
- Move failed-import primary-file cleanup out of `process_import_job` and retry handling into a scheduled background cleanup lifecycle:
  - `process_import_job` and `retry_import_job` must not delete original primary files, including after the last allowed attempt. Per-attempt secondary files may still be cleaned immediately.
  - Add a scheduled background job that finds import jobs which have remained `FAILED` longer than a configured retention period. The retention period must come from an environment-backed setting and must be evaluated using the current runtime value rather than snapshotted on each job.
  - The cleanup job deletes media files referenced by the failed job's primary `ImportJobSource` rows, marks the corresponding sources with a new `DELETED` status, and leaves non-file primary sources such as text and URLs intact unless a separate retention rule is approved.
  - After cleanup succeeds, move the import job to the new non-retryable terminal status `FAILED_FINALIZED`. The status preserves the failed outcome and explicitly indicates that failure cleanup/lifecycle finalization has completed.
  - Retry must be rejected for `FAILED_FINALIZED` regardless of `attempt_count` or the current maximum-attempt setting. The frontend must hide Retry for this status.
  - Make cleanup idempotent and safe under concurrent scheduler/worker execution. Define row-locking/claim behavior, partial storage-deletion handling, cleanup events and diagnostics, and whether a job remains `FAILED` when any referenced file could not be deleted.
  - Extend the scheduled cleanup/reconciliation job to remove orphaned recipe media left behind when best-effort filesystem cleanup after recipe deletion fails. Compare stored files with active `RecipeImage` and `ImportJobSource` storage keys before deletion, and keep the scan idempotent.
- Manual retry is initially allowed for every `FAILED` import, including failures such as `NOT_A_RECIPE` and `RECIPE_TOO_LONG`. Revisit whether some failure details should become explicitly non-retryable.
- During the authentication/users phase, distinguish user-triggered and admin-triggered import retries and define notification policy for each case. A user-triggered retry creates an `IMPORT_STARTED` notification; an admin-triggered retry may require different recipient, visibility, and audit behavior.
- Consider explicitly associating each import `JobEvent` with a concrete attempt number so admin diagnostics can group lifecycle events by attempt without inferring boundaries from timestamps and `IMPORT_STARTED` events.
- Distinguish silent video from genuine transcription failure. Preferred option: inspect the downloaded media for an audio stream with PyAV before calling the transcription provider. Lower-confidence fallback: classify known provider errors such as `Audio file processing failed`. Until then, both cases are recorded as failed transcript resources while the staged loader continues with any usable content.
- Add an environment-backed maximum duration for video audio tracks. When an audio track exceeds the configured limit, do not send it for transcription; record and handle the corresponding secondary resource as failed through the existing staged secondary-resource failure flow.
- Define the review behavior for a URL that was not the sole primary source but produced no successfully loaded secondary resources. The extractor receives no child evidence for that URL, so it cannot mark the primary URL as ignored through `ignoredSourceRefs`. Consider explicitly marking the URL resource as `IGNORED` from the staged loading result so the recipe receives a review flag.

## Tags

- Validate tag name and tag description length on both frontend and backend.
- Surface existing backend `DUPLICATE_TAG` and `TAG_LIMIT_EXCEEDED` errors on the Tags page instead of leaving mutation failures invisible.
- Show a persistent recipe-count badge/counter next to each tag. The existing tag-usage endpoint and delete confirmation already expose this count on demand.
- Add a way to navigate from a tag to the list of recipes containing that tag.
- Add tag sorting options.
- Add quick tag search/autocomplete by tag name.
- If `MAX_TAGS_PER_USER` becomes greater than backend `MAX_PAGE_LIMIT`, replace the recipe editor's current `limit=100` tag loading with a searchable/paginated tag picker.

## Ingredients

- Add frontend and backend length limits for ingredient `name`, `quantity`, `unit`, and `note`. Ingredient count and required-name validation already exist.
- Insert a newly added ingredient at the top of the editable ingredient list.
- Add ingredient reordering controls. Ingredient `position` is already persisted from the frontend array order; only the user-facing reordering interaction is missing.
- Add an ingredient calculator that scales quantities by the selected number of servings. The recipe `servings` field already exists in the model and API but is not yet exposed as a scaling workflow.
- Investigate semantically close ingredient terms such as `сахарозаменитель` and `подсластитель`: evaluate whether the current vector search handles them adequately before adding synonym normalization or query expansion.

## Recipes and Manual Content

- Add aligned frontend and backend length limits for every remaining editable recipe field, including title and author name. Ingredient count, instruction length, note length, and required ingredient names are already validated; backend validation remains authoritative.
- Normalize recipe-title formatting and casing using an explicitly defined locale-aware rule without corrupting brands, abbreviations, or proper names.
- Support fully manual recipes and standalone manual notes that can be added to collections alongside imported recipes. Clarify whether notes share a common collection-item abstraction with recipes or remain a separate entity.

## Notifications

- Add distinct colors and icons for different notification types while preserving accessible text/status cues.

## Flags and Review UX

- Revisit whether review concerns should use multiple flag types instead of one generic warning type. Define behavior when a recipe has more than one open flag, including aggregation, ordering, independent resolution, list-page indicators, recipe-detail messaging, and mobile/web UI/UX.

## Import History UX

- Evaluate whether users need a general Import History page in addition to notification history and direct ImportJob detail links. Before implementation, research the expected use cases, retention expectations, filtering/status needs, and retry/navigation UI. The current product intentionally relies on notifications plus per-job detail.

## Pagination and Lists

- Finish pagination-aware selectors on recipe detail. The main Recipes, Collections, and Tags pages already have pagination controls, but recipe detail still loads collections without paging controls and loads only the first 100 tags.
- Add sorting and filters for collections on backend and frontend.

## Улучшение серча

- Улучшить autocomplete для структурных концептов: если пользователь вводит текст, похожий на существующий tag (`низкокалорийное`, `быстрое`, `высокобелковое`, `без сахара`), явно предлагать выбрать tag chip. Пока не конвертировать free text в tag filter неявно.
- На Search Debug странице показывать, как был обработан запрос: только structured filters, semantic-only text или mixed chips + semantic text. Для semantic-only запросов показывать пояснение, что числовые/структурные фильтры не применялись.
- Добавить deterministic derived semantic labels в embedding input на основе структурных полей, не записывая их в `recipe_tags`: например `быстрое`/`quick` по `cook_time_minutes`, `низкокалорийное` по calories, `высокобелковое` по protein grams. Не генерировать эти labels через AI во время поиска.
- Ввести версию embedding input rules, например `EMBEDDING_INPUT_VERSION = "v2"`, и учитывать ее в input hash или input text. При изменении правил derived labels пересчитывать embeddings.
- При добавлении derived labels обновить правила invalidation/recompute: title, `ingredients.search_name`, instructions, `nutrition_estimate`, `cook_time_minutes`, версия правил derived labels.
- Позже рассмотреть строгие numeric filters: `maxCookTimeMinutes`, `maxCalories`, `minProteinGrams`, `maxCarbsGrams`. Не реализовывать до решения UX.
- До AI query parser добавить lightweight query concept suggestions: например `быстро` -> tag `быстрое` или будущий фильтр `до 20 минут`; `низкокалорийное` -> tag или будущий calorie filter.
- Перед настройкой ranking собрать небольшой ручной evaluation set с query, expected good recipe ids и expected bad recipe ids.
- Query expansion и hybrid ranking boosts оставить на более поздний этап после Search Debug, embedding input preview, derived labels и evaluation set.
- Возможный будущий hybrid score: semantic similarity + title match boost + ingredient query boost + tag match boost + derived property boost + recency/favorite boost. Не добавлять до понимания базового semantic behavior.
- Add pagination controls to Search Debug; currently it uses `limit=20`, `offset=0`.
- When autocomplete suggests one concrete recipe, selecting that recipe chip should navigate directly to recipe detail instead of adding a search filter.
