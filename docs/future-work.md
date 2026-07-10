# Future Work and Cleanup Notes

This document tracks known follow-up work, shortcuts, compatibility leftovers, and intentional deferrals that should not be forgotten after phase/subphase completion.

After each completed phase or subphase, review the finished work and propose candidate items to add here before moving on.

## AI and Import Pipeline

- Remove `sourcePosition` and `crop` from the Pydantic AI response schema for `coverCandidate`. They are currently kept as `None`-only legacy compatibility fields after the OpenAI response schema was narrowed to `sourceRef` and `confidence`.

## Background Processing

- Add a transactional outbox for embedding scheduling so persisted embedding lifecycle state and broker publishing are durably coordinated. Publishing is currently best-effort and intentionally secondary to completed user operations.

## Tags

- Validate tag name and tag description length on both frontend and backend.
- Show user-facing errors when creating a duplicate tag or exceeding the configured tag limit.
- Show a recipe-count badge/counter next to each tag.
- Add a way to navigate from a tag to the list of recipes containing that tag.
- Add tag sorting options.
- Add quick tag search/autocomplete by tag name.
- If `MAX_TAGS_PER_USER` becomes greater than backend `MAX_PAGE_LIMIT`, replace the recipe editor's current `limit=100` tag loading with a searchable/paginated tag picker.

## Ingredients

- Validate ingredient field lengths on both frontend and backend when editing recipes.

## Pagination and Lists

- Adapt frontend flows more fully to paginated recipe and collection responses where any remaining list usage still assumes full result sets.
- Add sorting and filters for collections on backend and frontend.

## Улучшение серча

- Улучшить autocomplete для структурных концептов: если пользователь вводит текст, похожий на существующий tag (`низкокалорийное`, `быстрое`, `высокобелковое`, `без сахара`), явно предлагать выбрать tag chip. Пока не конвертировать free text в tag filter неявно.
- На Search Debug странице показывать, как был обработан запрос: только structured filters, semantic-only text или mixed chips + semantic text. Для semantic-only запросов показывать пояснение, что числовые/структурные фильтры не применялись.
- Добавить deterministic derived semantic labels в embedding input на основе структурных полей, не записывая их в `recipe_tags`: например `быстрое`/`quick` по `cook_time_minutes`, `низкокалорийное` по calories, `высокобелковое` по protein grams. Не генерировать эти labels через AI во время поиска.
- Ввести версию embedding input rules, например `EMBEDDING_INPUT_VERSION = "v2"`, и учитывать ее в input hash или input text. При изменении правил derived labels пересчитывать embeddings.
- При добавлении derived labels обновить правила invalidation/recompute: title, `ingredients.search_name`, instructions, `nutrition_estimate`, `cook_time_minutes`, версия правил derived labels.
- Позже рассмотреть строгие numeric filters: `maxCookTimeMinutes`, `maxCalories`, `minProteinGrams`, `maxCarbsGrams`. Не реализовывать до решения UX.
- До AI query parser добавить lightweight query concept suggestions: например `быстро` -> tag `быстрое` или будущий фильтр `до 20 минут`; `низкокалорийное` -> tag или будущий calorie filter.
- Не менять vector metric как попытку улучшить качество без evidence. Текущая предпочтительная метрика: pgvector cosine distance (`<=>`), сортировка по distance ascending, debug similarity = `1 - distance`.
- Перед настройкой ranking собрать небольшой ручной evaluation set с query, expected good recipe ids и expected bad recipe ids.
- Query expansion и hybrid ranking boosts оставить на более поздний этап после Search Debug, embedding input preview, derived labels и evaluation set.
- Возможный будущий hybrid score: semantic similarity + title match boost + ingredient query boost + tag match boost + derived property boost + recency/favorite boost. Не добавлять до понимания базового semantic behavior.
- Add pagination controls to Search Debug; currently it uses `limit=20`, `offset=0`.
