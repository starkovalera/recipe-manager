# P10 — Presigned Media Access: Runbook and Review Checklist

Этот файл предназначен для ручного сопровождения работы Codex над P10.

Основная инструкция агенту:

```text
docs/handoffs/p10-presigned-media-access-codex-instructions.md
```

Утверждённый design spec:

```text
docs/superpowers/specs/2026-07-24-presigned-media-access-design.md
```

## 1. До запуска Codex

### Проверить состояние репозитория

- [ ] PR предыдущей backend-фазы смержен в `main`.
- [ ] `main` содержит P9 и P8B1.
- [ ] Независимый UI/UX PR не попал случайно в backend-ветку.
- [ ] Рабочая директория чистая.
- [ ] Локальный `main` синхронизирован с `origin/main`.

Команды:

```powershell
git status
git switch main
git pull --ff-only origin main
git log -5 --oneline
```

Ожидается, что в истории присутствуют изменения P9 и storage-backed maintenance.

### Проверить документацию P10

- [ ] Design spec просмотрен и соответствует согласованным решениям.
- [ ] В нём указаны `recipe_image` и `import_source_image`.
- [ ] Batch использует partial success.
- [ ] Access modes: `direct` и `authenticated_fetch`.
- [ ] S3 TTL: 60 секунд.
- [ ] S3 `HeadObject` запрещён.
- [ ] `MediaAccessService` выделен отдельно.
- [ ] Ownership/lifecycle правила совпадают с согласованными.
- [ ] Upload находится вне scope.

### Подготовить запуск агента

Передай Codex целиком файл:

```text
docs/handoffs/p10-presigned-media-access-codex-instructions.md
```

Codex должен:

- создать отдельную ветку от актуального `main`;
- не работать в `docs/p10-media-access-design`;
- сначала изучить актуальный код;
- реализовать фазу;
- открыть draft PR;
- не мержить PR.

Рекомендуемое имя ветки:

```text
codex/presigned-media-access
```

## 2. Что контролировать во время работы

Не нужно подтверждать каждую мелкую правку, но останови агента, если он предлагает изменить утверждённые контракты.

### Архитектурные стоп-сигналы

Нельзя продолжать без отдельного обсуждения, если Codex:

- [ ] предлагает вернуть storage key во frontend;
- [ ] предлагает сохранять presigned URL в БД;
- [ ] добавляет общую таблицу `Media`/`StorageObject`;
- [ ] помещает ownership-проверки в S3/LOCAL adapter;
- [ ] превращает `StorageService` в domain-aware сервис;
- [ ] заменяет partial success на fail-whole-batch;
- [ ] возвращает разные ошибки для missing и foreign ID;
- [ ] вводит `requiresAuth` вместо `accessMode`;
- [ ] трактует `direct` как `S3`, а `authenticated_fetch` как `LOCAL`;
- [ ] делает `HeadObject` для каждого grant;
- [ ] вводит upload flow в P10;
- [ ] проксирует S3 bytes через FastAPI;
- [ ] оставляет старый storage-key endpoint «для совместимости»;
- [ ] расширяет фазу до CDN, CloudFront, Terraform или public sharing;
- [ ] смешивает изменения UI/UX redesign PR с P10.

### Допустимые адаптации

Codex может самостоятельно:

- выбрать точные имена файлов в рамках утверждённых boundaries;
- использовать существующие repository/query patterns;
- разбить frontend batching на hook/provider/cache;
- переиспользовать существующий boto3 client безопасным способом;
- улучшить focused code structure в непосредственно затронутых местах;
- добавить дополнительные regression tests.

## 3. Проверка diff

После открытия PR сначала посмотри общую форму изменений.

```powershell
git fetch origin
git diff --stat origin/main...origin/codex/presigned-media-access
git diff --name-only origin/main...origin/codex/presigned-media-access
```

### Ожидаемые области

Backend:

```text
backend/app/media/
backend/app/api/routes/media.py
backend/app/schemas/media.py
backend/app/schemas/recipes.py
backend/app/schemas/imports.py
backend/app/storage/
backend/app/core/errors.py
backend/tests/media/
backend/tests/api/test_media.py
backend/tests/storage/
```

Frontend:

```text
frontend/src/api/client.ts
frontend/src/api/types.ts
frontend/src/components/
frontend/src/pages/RecipeDetailPage.tsx
frontend/src/pages/ImportJobDetailPage.tsx
frontend/src/components/RecipeGrid.tsx
соответствующие тесты
```

Gateway/docs:

```text
infra/krakend/config/endpoints.json
backend/tests/infra/test_krakend_config.py
docs/media-access.md
docs/s3-storage.md
docs/architecture/production-roadmap.md
docs/implementation-plan.md
README.md или docs/api.md при необходимости
```

### Неожиданные области

Потребуй объяснение, если diff затрагивает:

- Terraform/AWS provisioning;
- unrelated queue/Lambda code;
- auth provider lifecycle;
- migrations;
- UI/UX design workspace;
- broad model refactoring;
- unrelated recipe/import behavior.

## 4. Обязательный review backend

### Public API

- [ ] `RecipeImageOut` больше не содержит `mediaUrl`.
- [ ] `ImportJobSourceOut` содержит стабильный `id`.
- [ ] Public responses не содержат `storageKey`.
- [ ] `POST /media/access` требует auth.
- [ ] Batch limit равен 100.
- [ ] Extra fields запрещены.
- [ ] Результаты возвращаются в исходном порядке.
- [ ] Дубликаты сохраняются по позициям.
- [ ] Для каждого item есть ровно `grant` или `error`.
- [ ] Missing и foreign дают одинаковый `MEDIA_NOT_FOUND`.
- [ ] Provider-wide failure даёт batch-level `503`.

### Ownership

`recipe_image`:

- [ ] Проверяется владелец recipe.
- [ ] Recipe должен быть `ACTIVE`.
- [ ] Статус связанного resource не влияет на доступ.
- [ ] Detached image не выдаётся.

`import_source_image`:

- [ ] Проверяется владелец import job.
- [ ] Source должен быть `IMAGE`.
- [ ] Нужен `image_storage_key`.
- [ ] `FAILED` сохраняет доступ.
- [ ] `FAILED_ARTIFACTS_REMOVED` запрещает доступ.

### Boundaries

- [ ] Есть отдельный `MediaAccessService`.
- [ ] Есть строгий resolver registry.
- [ ] Route не содержит domain query logic.
- [ ] Storage adapter не содержит ownership logic.
- [ ] `StorageService` не стал user/domain-aware.
- [ ] Runtime provider выбирается централизованно.
- [ ] Нет `isinstance(LocalStorageService)` в media route.

### S3

- [ ] Presign использует `get_object`.
- [ ] Bucket берётся из `USER_MEDIA`.
- [ ] TTL — 60 секунд.
- [ ] `expiresAt` UTC-aware.
- [ ] Нет `HeadObject`.
- [ ] Client остаётся lazy/reused.
- [ ] URL/signature не логируются.
- [ ] SDK failures корректно переходят в `503`.

### LOCAL

- [ ] Grant использует `authenticated_fetch`.
- [ ] URL содержит media type и media ID.
- [ ] URL не содержит storage key.
- [ ] GET повторно проверяет auth и ownership.
- [ ] Используется `FileResponse`, без загрузки всего файла в память.
- [ ] Path traversal блокируется существующей LOCAL boundary.
- [ ] В S3 runtime route не проксирует S3 bytes.

## 5. Обязательный review frontend

- [ ] Типы основаны на media reference, а не `mediaUrl`.
- [ ] `mediaUrl()` удалён.
- [ ] `isApiMediaUrl()` удалён.
- [ ] Нет решений по форме URL.
- [ ] Есть batch API client.
- [ ] Recipe grid батчит cover references.
- [ ] Recipe detail батчит cover/options/images.
- [ ] Import detail батчит image sources.
- [ ] `direct` передаётся непосредственно в `src`.
- [ ] `authenticated_fetch` использует authenticated API client.
- [ ] Blob object URL освобождается через `URL.revokeObjectURL`.
- [ ] Есть комментарий про невозможность добавить bearer token в обычный `<img src>`.
- [ ] Частичная ошибка одного media не ломает остальные.
- [ ] Default SVG продолжает работать без grant.
- [ ] Expired direct grant обновляется.
- [ ] Query keys основаны на `(type, id)`, а не временном URL.

## 6. Проверка документации и комментариев

### `docs/media-access.md`

- [ ] Документ создан.
- [ ] Объясняет stable ID / storage key / access URL.
- [ ] Содержит request/response examples.
- [ ] Описывает partial success.
- [ ] Описывает indistinguishable missing/foreign.
- [ ] Объясняет оба access mode.
- [ ] Отдельно объясняет, почему это не `requiresAuth`.
- [ ] Описывает LOCAL.
- [ ] Описывает S3 и TTL.
- [ ] Фиксирует отсутствие `HeadObject`.
- [ ] Фиксирует logging restrictions.
- [ ] Фиксирует `DownloadGrant != UploadIntent`.
- [ ] Не заявляет, что `direct` означает public.
- [ ] Не заявляет, что access mode равен provider.

### Комментарии в коде

- [ ] Комментарий на `DIRECT`.
- [ ] Комментарий на `AUTHENTICATED_FETCH`.
- [ ] Комментарий/docstring на `DownloadGrant.access_mode`.
- [ ] Frontend comment рядом с authenticated fetch.
- [ ] Комментарии объясняют причину, а не пересказывают код.

## 7. Автоматические проверки

Запусти локально независимо от отчёта Codex.

### Backend

```powershell
cd backend
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Запиши:

- количество passed;
- количество skipped;
- наличие warnings;
- точную причину любого xfail/skip.

### Frontend

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test:ci
pnpm build
```

### Gateway

Из корня:

```powershell
make gateway-check
```

### PostgreSQL/Alembic

Даже если миграции нет:

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
```

При наличии новой migration останови review и выясни, зачем она понадобилась.

## 8. Поисковые проверки legacy flow

Из корня репозитория:

```powershell
rg "mediaUrl|media_url|build_media_url|isApiMediaUrl|/media/\{namespace\}|legacy-media" backend frontend infra docs
```

Проверь вручную каждое совпадение.

Разрешены только:

- migration/history/design documentation, где legacy flow упоминается как удалённый;
- negative assertions в тестах.

В production code старого flow быть не должно.

Проверить публичные storage keys:

```powershell
rg "storage_key|storageKey" backend/app/schemas frontend/src
```

Каждое совпадение должно быть internal/excluded или отсутствовать в public types.

Проверить отсутствие HEAD:

```powershell
rg "head_object|HeadObject|head_calls" backend/app backend/tests
```

В production code вызова быть не должно. В тестах допускается negative assertion.

## 9. Ручная LOCAL/PREVIEW проверка

Проверяй через KrakenD.

Запусти инфраструктуру:

```powershell
make infra-up
```

Запусти backend/worker/frontend привычным способом с `APP_ENV=PREVIEW`.

### Основной flow

- [ ] Recipe list показывает covers.
- [ ] Recipe detail показывает hero cover.
- [ ] Cover options показывают изображения.
- [ ] Preview/modal открывается.
- [ ] Import job показывает submitted image sources.
- [ ] В Network виден `POST /media/access`.
- [ ] Grant имеет `accessMode=authenticated_fetch`.
- [ ] Следующий GET имеет форму `/media/{type}/{id}`.
- [ ] В URL нет storage key.
- [ ] GET отправляет bearer authorization.
- [ ] Blob URL освобождается при закрытии/смене изображения.
- [ ] Нет лишних запросов по одному на каждую картинку, когда доступен batch.

### Security/lifecycle

- [ ] ID другого пользователя не раскрывает существование.
- [ ] Missing ID выглядит так же.
- [ ] Неактивный recipe не получает grant.
- [ ] Resource status `DELETED` сам по себе не запрещает owned active recipe image.
- [ ] `FAILED` import source доступен до cleanup.
- [ ] После cleanup и `FAILED_ARTIFACTS_REMOVED` grant не выдаётся.
- [ ] Прямой GET без auth не отдаёт файл.

## 10. Ручная S3 проверка

Используй только private test bucket и тестовые данные.

- [ ] Backend стартует с `STORAGE_PROVIDER=S3`.
- [ ] Owned media получает `accessMode=direct`.
- [ ] `expiresAt` примерно через 60 секунд.
- [ ] URL загружается браузером напрямую.
- [ ] Backend не проксирует bytes.
- [ ] URL отсутствует в backend/frontend logs.
- [ ] Missing и foreign возвращают одинаковый item error.
- [ ] Bucket name и storage key отсутствуют в domain API.
- [ ] После истечения URL перестаёт работать или обновляется новым grant.
- [ ] DB row на отсутствующий объект получает signed URL, а GET возвращает S3 `404`.
- [ ] В CloudTrail/debug logs нет `HeadObject` от access flow, если такая проверка доступна.

Если S3 smoke не выполнялся, это должно быть явно написано в PR `Verification gaps`.

## 11. Review PR

PR должен быть draft и направлен в `main`.

Проверь наличие разделов:

```text
## Scope
## Explicitly deferred
## Automated verification
## Manual verification
## Verification gaps
## Security notes
```

Нельзя мержить, если:

- есть незакрытый verification gap, влияющий на correctness/security;
- failed тесты;
- live проверка заявлена без доказательств;
- сохранён legacy endpoint;
- storage keys выходят наружу;
- missing/foreign различимы;
- S3 URL логируется;
- есть HEAD-per-grant;
- ownership находится в adapter/route;
- upload scope добавлен без отдельного design;
- frontend продолжает использовать URL-shape logic.

## 12. После успешного review

- [ ] Все CI checks зелёные.
- [ ] Draft PR переведён в ready только после review.
- [ ] PR смержен выбранным для проекта способом.
- [ ] Локальный `main` обновлён.
- [ ] Проверено, что roadmap/documentation отражают завершённый P10.
- [ ] Удалена implementation branch после merge.
- [ ] Зафиксированы фактические pass counts и manual smoke results.
- [ ] Следующая фаза обсуждается отдельно; scope не добавляется задним числом в P10.
