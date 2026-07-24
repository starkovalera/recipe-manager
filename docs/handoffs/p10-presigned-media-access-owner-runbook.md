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

## 3. Что Codex обязан проверить самостоятельно

Твоя задача — не просматривать глазами весь набор изменённых файлов и не повторять за агентом механические проверки. До передачи PR на review Codex должен сам выполнить полный audit и приложить доказательства в PR body или отдельный PR comment.

Codex обязан предоставить один структурированный verification report со следующими разделами.

### Scope и diff audit

Codex сам выполняет:

```powershell
git fetch origin
git diff --check origin/main...HEAD
git diff --stat origin/main...HEAD
git diff --name-only origin/main...HEAD
git log --oneline origin/main..HEAD
```

В отчёте он должен:

- перечислить все изменённые файлы, сгруппировав их по `backend`, `frontend`, `gateway`, `docs`, `tests`;
- для каждого неожиданного файла объяснить, почему он нужен P10;
- подтвердить, что migrations, Terraform, unrelated queue/Lambda/auth и UI/UX redesign не затронуты;
- подтвердить отсутствие whitespace/conflict-marker ошибок по `git diff --check`;
- отдельно перечислить удалённые legacy-файлы и helpers.

### Автоматические проверки

Codex сам запускает и приводит точные результаты, включая pass counts, skips и warnings:

```powershell
cd backend
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run alembic upgrade head
uv run alembic current

cd ..\frontend
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test:ci
pnpm build

cd ..
make gateway-check
```

Если команда не запускалась, Codex обязан назвать точную причину. Формулировки «должно работать» или «покрыто тестами» без свежего результата не принимаются.

### Автоматический audit контрактов и legacy flow

Codex сам выполняет поисковые проверки и классифицирует каждое совпадение:

```powershell
rg "mediaUrl|media_url|build_media_url|isApiMediaUrl|/media/\{namespace\}|legacy-media" backend frontend infra docs
rg "storage_key|storageKey" backend/app/schemas frontend/src
rg "head_object|HeadObject|head_calls" backend/app backend/tests
rg "requiresAuth|requires_auth" backend frontend docs
rg "isinstance\(.*LocalStorageService" backend/app
```

В отчёте он должен подтвердить:

- legacy production flow удалён;
- storage keys отсутствуют в public schemas и frontend types;
- `HeadObject` отсутствует в production access path;
- `requiresAuth` не введён вместо `accessMode`;
- media route не выбирает provider через `isinstance`;
- допустимые совпадения относятся только к negative tests, migration/history или документации об удалённом поведении.

### Архитектурный audit

Codex сам проверяет и документирует:

- где находится `MediaAccessService`;
- где находится strict resolver registry;
- где выполняются ownership/lifecycle queries;
- где находится runtime download-access provider selection;
- что `StorageService` не получил domain/user-aware методы;
- что route не содержит domain query logic;
- что LOCAL/S3 providers не содержат ownership logic;
- что frontend выбирает retrieval behavior только по `accessMode`;
- что `DownloadGrant` и будущий `UploadIntent` не объединены.

Для каждого пункта Codex приводит точный путь файла и имя класса/функции. Тебе не нужно искать эти места самостоятельно по всему diff.

### Security и API audit

Codex сам подтверждает тестами и ссылками на test cases:

- missing и foreign media неразличимы;
- partial success сохраняет успешные siblings;
- input order и duplicate positions сохраняются;
- recipe/import ownership и lifecycle rules реализованы полностью;
- LOCAL GET повторно авторизует domain reference;
- S3 presign использует TTL 60 и не делает HEAD;
- presigned URL/signature не логируется;
- public domain responses не содержат storage keys или `mediaUrl`.

### Карта ключевого review для человека

В конце отчёта Codex должен дать короткую таблицу из 6–10 ключевых точек:

```text
Решение | Файл | Класс/функция или диапазон строк | Что проверить глазами
```

Карта должна включать минимум:

- public request/response schemas;
- `MediaAccessService`;
- recipe/import resolvers;
- LOCAL provider/route;
- S3 presign provider;
- frontend media grant component/hook;
- gateway routes;
- `docs/media-access.md`;
- обязательные комментарии про `accessMode`.

## 4. Что проверить тебе в diff

Не нужно сверять каждый файл с декларативным списком. Используй verification report Codex и просмотри только ключевые решения.

### Обязательные точки

- [ ] В API-примере `POST /media/access` используются только `type` и domain `id`.
- [ ] В response есть `accessMode`, а не `requiresAuth` или provider name.
- [ ] `MEDIA_NOT_FOUND` одинаков для missing и foreign.
- [ ] `MediaAccessService` действительно отдельный слой, а не тонкое имя над route logic.
- [ ] Ownership находится в query/application layer, а не в storage providers.
- [ ] S3 provider содержит `ExpiresIn=60` и не содержит HEAD-проверки.
- [ ] LOCAL URL имеет форму `/media/{media_type}/{media_id}` и не содержит storage key.
- [ ] Frontend ветвится по `direct` / `authenticated_fetch`, а не по URL или provider.
- [ ] В коде есть согласованные поясняющие комментарии.
- [ ] `docs/media-access.md` понятно объясняет контракт и границу с будущим upload.
- [ ] В PR нет migrations, Terraform, CDN/CloudFront, upload flow или UI redesign.

Если карта Codex не позволяет быстро найти эти места, верни PR агенту и попроси дополнить verification report. Не ищи их вручную во всём репозитории.

## 5. Внешняя подготовка, которую Codex не может выполнить за тебя

### Clerk / PREVIEW

Подготовь минимум одного Clerk development user. Для проверки foreign ID удобнее иметь двух пользователей: A и B.

Если локального файла ещё нет:

```powershell
cd C:\Users\stark\Documents\recipe-manager
if (-not (Test-Path backend\config\preview-users.local.toml)) {
    Copy-Item backend\config\preview-users.example.toml backend\config\preview-users.local.toml
}
notepad backend\config\preview-users.local.toml
```

Заполни реальные `auth_user_id` и email. Для двух пользователей добавь два блока `[[users]]`. Не коммить этот файл.

Проверь наличие локальных env-файлов:

```powershell
Test-Path .env
Test-Path backend\.env
Test-Path frontend\.env
```

Ожидается три значения `True`.

Не печатай secret values в PR или чат Codex. Проверь вручную, что:

- root `.env` содержит `CLERK_ISSUER` и `CLERK_JWKS_URL`;
- `backend/.env` содержит Clerk backend secrets и `PREVIEW_USERS_FILE=./config/preview-users.local.toml`;
- `frontend/.env` содержит `VITE_API_BASE_URL=http://127.0.0.1:8081` и Clerk publishable key.

### Тестовые изображения

Подготовь два небольших изображения JPEG/PNG, например:

```text
C:\Temp\p10-image-1.jpg
C:\Temp\p10-image-2.jpg
```

Они нужны, чтобы recipe detail содержал несколько media references и batch был виден в Network.

### AWS для отдельной S3-проверки

Для live S3 smoke нужны подготовленные вне Codex:

- private test bucket;
- AWS credentials в стандартной boto3 credential chain;
- разрешения минимум на presign/get для тестовых объектов;
- тестовая конфигурация bucket name и region;
- данные, которые можно безопасно удалить.

Если этого нет, S3 live smoke помечается как verification gap. Автоматические provider tests всё равно обязательны.

## 6. Пошаговая ручная LOCAL/PREVIEW проверка

Проверка выполняется через KrakenD на `http://127.0.0.1:8081`, не через прямой FastAPI upstream.

### Шаг 1. Переключиться на implementation branch

Открой PowerShell:

```powershell
cd C:\Users\stark\Documents\recipe-manager
git fetch origin
git switch codex/presigned-media-access
git pull --ff-only origin codex/presigned-media-access
git status
```

Ожидаемый результат: рабочая директория чистая.

### Шаг 2. Запустить PostgreSQL, Redis, Adminer и KrakenD

**Терминал 1:**

```powershell
cd C:\Users\stark\Documents\recipe-manager
docker compose up -d --build postgres redis adminer krakend
docker compose ps
curl.exe http://127.0.0.1:8081/__health
```

Ожидается:

- `postgres` и `redis` имеют healthy status;
- `adminer` и `krakend` запущены;
- `/__health` отвечает успешно.

`/health` пока может не отвечать, потому что backend ещё не запущен.

### Шаг 3. Запустить backend в PREVIEW

**Терминал 2:**

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv sync --frozen
$env:APP_ENV="PREVIEW"
uv run fastapi dev app/main.py --host 127.0.0.1 --port 8010
```

Дождись завершения startup/migrations без traceback.

Важно: PREVIEW startup пересоздаёт preview schema и очищает `backend/storage/preview`. После создания тестовых данных не перезапускай backend до конца smoke-проверки.

### Шаг 4. Засеять PREVIEW users

**Терминал 3:**

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
$env:APP_ENV="PREVIEW"
uv run python -m app.local.seed_preview_users
curl.exe http://127.0.0.1:8081/health
```

Ожидается успешное завершение seed-команды и успешный `/health` через KrakenD.

Если seed сообщает, что пользователь Clerk не найден или конфигурация некорректна, исправь `preview-users.local.toml` до продолжения.

### Шаг 5. Запустить worker

**Терминал 4:**

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
$env:APP_ENV="PREVIEW"
uv run dramatiq app.worker
```

Оставь worker запущенным. Он нужен для import и embedding jobs.

### Шаг 6. Запустить frontend

**Терминал 5:**

```powershell
cd C:\Users\stark\Documents\recipe-manager\frontend
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1
```

Открой:

```text
http://127.0.0.1:5173
```

Войди как пользователь A.

### Шаг 7. Создать тестовый import с несколькими изображениями

1. Открой страницу импорта.
2. Добавь `C:\Temp\p10-image-1.jpg` и `C:\Temp\p10-image-2.jpg`.
3. Добавь текст:

```text
Название: Тестовый горячий бутерброд.
Ингредиенты: хлеб, сыр.
Инструкция: положить сыр на хлеб и запечь до расплавления.
```

4. Отправь import.
5. Дождись terminal success status.
6. Запиши URL import detail и recipe ID, созданный import.
7. Не перезапускай backend.

Если import падает из-за внешнего AI provider, для PREVIEW smoke переключи локальную конфигурацию на поддерживаемый fake/auto provider согласно текущей документации проекта и повтори после нового PREVIEW startup.

### Шаг 8. Проверить пользовательский flow

В браузере проверь последовательно:

1. Recipe list показывает cover без broken image.
2. Recipe detail показывает hero cover.
3. Cover options содержат загруженные изображения.
4. Клик по source image открывает preview/modal.
5. Import detail показывает оба submitted image sources.
6. Закрытие modal и переход между страницами не приводит к видимым ошибкам в Console.
7. Default SVG продолжает показываться там, где media reference отсутствует.

### Шаг 9. Проверить LOCAL media protocol в DevTools

1. Открой DevTools → **Network**.
2. Включи **Preserve log**.
3. Очисти список запросов.
4. Открой recipe detail с двумя изображениями.
5. В фильтре Network введи `media`.
6. Найди `POST /media/access`.
7. Открой **Payload** и проверь:
   - items содержат `type` и `id`;
   - storage key отсутствует;
   - при нескольких изображениях запрос содержит несколько items, а не отдельный POST на каждое изображение.
8. Открой **Response** и проверь:
   - успешные items имеют `accessMode: "authenticated_fetch"`;
   - `expiresAt` равен `null`;
   - URL имеет форму `/media/recipe_image/<id>` или `/media/import_source_image/<id>`;
   - URL не содержит `recipes/media`, `imports/source`, owner ID, bucket name или имя файла.
9. Найди следующий `GET /media/{media_type}/{media_id}`.
10. В **Request Headers** проверь наличие `Authorization: Bearer ...`.
11. В **Response Headers** проверь корректный image content type.
12. Убедись, что сам GET URL содержит domain ID, а не storage key.

Bearer token не копируй в issue, PR или чат.

### Шаг 10. Проверить partial success без ручного получения токена

1. В Network выбери успешный `POST /media/access`.
2. Правой кнопкой → **Copy** → **Copy as fetch**.
3. Открой DevTools → **Console**.
4. Вставь скопированную команду, но перед запуском измени body так, чтобы он содержал:
   - один существующий `type`/`id` из успешного запроса;
   - второй item того же type с `id: "missing-p10-media-id"`.
5. Оберни fetch так, чтобы увидеть JSON, например:

```javascript
await (await fetch(/* скопированные URL и options */)).json()
```

6. Запусти команду.

Ожидается:

- HTTP request завершается успешно;
- существующий item содержит `grant`;
- missing item содержит `error.code === "MEDIA_NOT_FOUND"`;
- успешный item не исчезает из-за ошибки sibling.

### Шаг 11. Проверить, что LOCAL GET требует auth

1. Скопируй полный URL одного `GET /media/{media_type}/{media_id}`.
2. Открой новое окно Incognito/Private, где нет Clerk session.
3. Вставь URL в адресную строку.

Ожидается `401`/`403` или эквивалентный gateway auth error. Изображение не должно открыться.

### Шаг 12. Проверить foreign ID вторым пользователем

Этот шаг выполняется, если подготовлен пользователь B.

1. Сохрани media type и media ID пользователя A.
2. В отдельном Incognito/другом browser profile войди как пользователь B.
3. Открой DevTools → Network и выполни любое authenticated действие, чтобы получить запрос с токеном B.
4. Скопируй request как fetch.
5. Измени URL на `http://127.0.0.1:8081/media/access`, method на `POST`, `Content-Type` на `application/json`, а body на reference пользователя A.
6. Выполни fetch и прочитай JSON.

Ожидается тот же per-item `MEDIA_NOT_FOUND`, что и для `missing-p10-media-id`. Ответ не должен сообщать, что объект принадлежит другому пользователю.

Если второго пользователя нет, зафиксируй, что live foreign-user smoke не выполнен; Codex обязан предоставить automated test evidence.

### Шаг 13. Что не нужно проверять вручную

Не изменяй БД вручную ради edge cases. Следующие случаи проверяет Codex автоматизированными тестами и отражает в verification report:

- inactive/deletion-pending recipe;
- `RecipeResource.status=DELETED` при active owned recipe;
- detached `RecipeImage`;
- non-image import source;
- null storage key;
- `FAILED` против `FAILED_ARTIFACTS_REMOVED`;
- duplicate-position preservation;
- bounded query count;
- Blob URL revocation;
- direct grant expiry refresh;
- no `HeadObject`;
- provider-wide `503`.

### Шаг 14. Завершить LOCAL/PREVIEW smoke

Сохрани в review notes:

- browser и его версию;
- commit SHA implementation branch;
- какие шаги 8–12 выполнены;
- скриншот или краткую запись Network request/response без bearer token и presigned secrets;
- все обнаруженные ошибки.

Останови frontend, worker и backend через `Ctrl+C` в соответствующих терминалах.

**Терминал 1:**

```powershell
cd C:\Users\stark\Documents\recipe-manager
docker compose down
```

## 7. Ручная S3 проверка

Используй только private test bucket и тестовые данные. Действия в AWS и выдача credentials остаются на тебе; Codex не должен имитировать или заявлять их выполнение.

- [ ] Backend запущен с тестовой конфигурацией `STORAGE_PROVIDER=S3`.
- [ ] Owned media получает `accessMode=direct`.
- [ ] `expiresAt` примерно через 60 секунд.
- [ ] URL загружается браузером напрямую.
- [ ] Backend не проксирует bytes.
- [ ] URL отсутствует в backend/frontend logs.
- [ ] Missing и foreign возвращают одинаковый item error.
- [ ] Bucket name и storage key отсутствуют в domain API.
- [ ] После истечения URL перестаёт работать или frontend получает новый grant.
- [ ] DB row на отсутствующий объект получает signed URL, а GET возвращает S3 `404`.
- [ ] В CloudTrail/debug logs нет `HeadObject` от access flow, если такая проверка доступна.

Если S3 smoke не выполнялся, это должно быть явно написано в PR `Verification gaps`.

## 8. Review PR и merge blockers

PR должен быть draft и направлен в `main`.

Проверь наличие разделов:

```text
## Scope
## Explicitly deferred
## Automated verification
## Diff and architecture audit
## Manual verification
## Verification gaps
## Security notes
## Key human review map
```

Проверь, что verification report Codex содержит фактические команды, результаты и карту ключевых файлов.

Нельзя мержить, если:

- Codex не предоставил полный self-audit;
- есть незакрытый verification gap, влияющий на correctness/security;
- failed tests или незелёные CI checks;
- live проверка заявлена без доказательств;
- сохранён legacy endpoint;
- storage keys выходят наружу;
- missing/foreign различимы;
- S3 URL логируется;
- есть HEAD-per-grant;
- ownership находится в adapter/route;
- upload scope добавлен без отдельного design;
- frontend продолжает использовать URL-shape logic;
- в diff появились необъяснённые migrations, Terraform, unrelated backend или UI redesign изменения.

## 9. После успешного review

- [ ] Все CI checks зелёные.
- [ ] Ручной LOCAL/PREVIEW smoke выполнен и записан.
- [ ] S3 smoke выполнен либо честно указан как gap с оценкой риска.
- [ ] Ключевые точки diff просмотрены по карте Codex.
- [ ] Draft PR переведён в ready только после review.
- [ ] PR смержен выбранным для проекта способом.
- [ ] Локальный `main` обновлён.
- [ ] Проверено, что roadmap/documentation отражают завершённый P10.
- [ ] Удалена implementation branch после merge.
- [ ] Зафиксированы фактические pass counts и manual smoke results.
- [ ] Следующая фаза обсуждается отдельно; scope не добавляется задним числом в P10.
