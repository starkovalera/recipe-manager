# P10 — Presigned Media Access: Owner Runbook

Этот файл предназначен для сопровождения работы Codex над P10.

Передай агенту:

```text
docs/handoffs/p10-presigned-media-access-codex-instructions.md
```

Утверждённый design:

```text
docs/superpowers/specs/2026-07-24-presigned-media-access-design.md
```

## 1. Как Codex должен работать

Codex сначала выполняет один readiness check.

Он проверяет доступ к репозиторию и `origin`, актуальный `main`, наличие design/instruction files, рабочее состояние и возможность установить зависимости из lockfiles.

Если всё есть, он сразу:

1. создаёт feature branch от актуального `main`;
2. изучает код и тесты;
3. реализует всю фазу;
4. запускает проверки и self-audit;
5. обновляет документацию;
6. коммитит и пушит изменения;
7. открывает draft PR;
8. передаёт тебе весь PR на единое review.

Он не должен просить подтверждение плана, имени ветки, разбивки задач, отдельных файлов, тестов, коммитов или каждого следующего шага.

Вопрос допустим только при реальном блокере:

- design буквально противоречит актуальному коду;
- возникла новая существенная развилка в architecture/security/public API/migration/scope;
- нужен внешний prerequisite, который можешь предоставить только ты;
- требуется расширить scope;
- требуется необратимое действие без разрешения.

Codex не мержит PR.

## 2. Что подготовить до запуска

### Репозиторий

Убедись, что предыдущие backend-фазы смержены в `main`, а независимый UI/UX PR не смешан с P10.

```powershell
cd C:\Users\stark\Documents\recipe-manager
git status
git switch main
git pull --ff-only origin main
git log -5 --oneline
```

### Clerk / PREVIEW

Нужен минимум один Clerk development user. Для live foreign-user проверки удобнее два пользователя: A и B.

Если файла ещё нет:

```powershell
cd C:\Users\stark\Documents\recipe-manager
if (-not (Test-Path backend\config\preview-users.local.toml)) {
    Copy-Item backend\config\preview-users.example.toml backend\config\preview-users.local.toml
}
notepad backend\config\preview-users.local.toml
```

Заполни реальные `auth_user_id` и email. Для второго пользователя добавь второй блок `[[users]]`. Не коммить файл.

Проверь наличие env-файлов:

```powershell
Test-Path .env
Test-Path backend\.env
Test-Path frontend\.env
```

Ожидается три `True`.

Проверь вручную, не печатая secrets:

- root `.env`: `CLERK_ISSUER`, `CLERK_JWKS_URL`;
- `backend/.env`: Clerk secrets и `PREVIEW_USERS_FILE=./config/preview-users.local.toml`;
- `frontend/.env`: `VITE_API_BASE_URL=http://127.0.0.1:8081` и Clerk publishable key.

### Тестовые данные

Подготовь два небольших изображения:

```text
C:\Temp\p10-image-1.jpg
C:\Temp\p10-image-2.jpg
```

Они нужны, чтобы увидеть batching нескольких media references.

### AWS для live S3 smoke

Нужны только для отдельной ручной проверки:

- private non-production bucket;
- AWS credentials в стандартной credential chain;
- регион и bucket name;
- права на test objects;
- данные, которые можно удалить.

Если этого нет, live S3 smoke остаётся verification gap. Автоматические provider tests всё равно обязательны.

## 3. Что Codex обязан проверить самостоятельно

Ты не должна просматривать весь diff, повторять всю test suite или вручную классифицировать поисковые результаты.

До передачи PR Codex обязан приложить структурированный verification report.

### Diff/scope audit

Он запускает:

```bash
git fetch origin
git diff --check origin/main...HEAD
git diff --stat origin/main...HEAD
git diff --name-only origin/main...HEAD
git log --oneline origin/main..HEAD
```

И самостоятельно:

- группирует все изменённые файлы по backend/frontend/gateway/docs/tests;
- объясняет неожиданные файлы;
- подтверждает, были ли затронуты migrations, Terraform, unrelated queue/Lambda/auth и UI/UX workspace;
- перечисляет удалённые legacy helpers/routes;
- приводит результат `git diff --check`.

### Automated verification

Codex запускает:

```bash
cd backend
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run alembic upgrade head
uv run alembic current

cd ../frontend
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test:ci
pnpm build

cd ..
make gateway-check
```

В отчёте должны быть pass counts, skips, warnings, failures и причины всего, что не запускалось.

### Legacy/security/boundary audit

Codex сам выполняет и классифицирует каждое совпадение:

```bash
rg "mediaUrl|media_url|build_media_url|isApiMediaUrl|/media/\{namespace\}|legacy-media" backend frontend infra docs
rg "storage_key|storageKey" backend/app/schemas frontend/src
rg "head_object|HeadObject|head_calls" backend/app backend/tests
rg "requiresAuth|requires_auth" backend frontend docs
rg "isinstance\(.*LocalStorageService" backend/app
```

Он должен доказать отсутствие legacy production flow, public storage keys, HEAD-per-grant, `requiresAuth` вместо `accessMode` и route-level provider switch.

### Architecture audit

Codex указывает точные paths и class/function names для:

- `MediaAccessService`;
- strict resolver registry;
- recipe/import ownership queries;
- runtime provider selection;
- LOCAL route/provider;
- S3 presign provider;
- frontend batching/grant cache;
- gateway routes;
- обязательных comments.

В конце он даёт короткую карту из 6–10 точек:

```text
Decision | File | Class/function or line range | What to inspect
```

Если этой карты недостаточно для быстрого review, верни PR агенту на дополнение. Не ищи самостоятельно нужные места по сотням файлов.

## 4. Что посмотреть тебе в PR

Проверь только ключевые решения:

- request использует только media `type` и domain `id`;
- response содержит `accessMode`, а не provider или `requiresAuth`;
- missing и foreign возвращают одинаковый `MEDIA_NOT_FOUND`;
- `MediaAccessService` действительно отдельный application layer;
- ownership queries не находятся в route/storage provider;
- S3 использует `ExpiresIn=60` и не делает HEAD;
- LOCAL URL имеет `/media/{media_type}/{media_id}` и не содержит storage key;
- frontend ветвится только по `direct` / `authenticated_fetch`;
- присутствуют согласованные explanatory comments;
- `docs/media-access.md` объясняет контракт и границу с будущим upload;
- PR не содержит migration, Terraform, CDN/CloudFront, upload flow или UI redesign.

## 5. Пошаговая LOCAL/PREVIEW проверка

Проверяй через KrakenD `http://127.0.0.1:8081`, не через прямой FastAPI upstream.

### Шаг 1. Переключиться на implementation branch

```powershell
cd C:\Users\stark\Documents\recipe-manager
git fetch origin
git switch codex/presigned-media-access
git pull --ff-only origin codex/presigned-media-access
git status
```

Ожидается clean working tree.

### Шаг 2. Запустить инфраструктуру

**Терминал 1:**

```powershell
cd C:\Users\stark\Documents\recipe-manager
docker compose up -d --build postgres redis adminer krakend
docker compose ps
curl.exe http://127.0.0.1:8081/__health
```

Ожидается healthy PostgreSQL/Redis и успешный KrakenD health.

### Шаг 3. Запустить backend в PREVIEW

**Терминал 2:**

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv sync --frozen
$env:APP_ENV="PREVIEW"
uv run fastapi dev app/main.py --host 127.0.0.1 --port 8010
```

Дождись startup без traceback. PREVIEW пересоздаёт schema и очищает preview storage; после создания данных не перезапускай backend до конца проверки.

### Шаг 4. Засеять users

**Терминал 3:**

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
$env:APP_ENV="PREVIEW"
uv run python -m app.local.seed_preview_users
curl.exe http://127.0.0.1:8081/health
```

Ожидается успешный seed и `/health` через KrakenD.

### Шаг 5. Запустить worker

**Терминал 4:**

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
$env:APP_ENV="PREVIEW"
uv run dramatiq app.worker
```

### Шаг 6. Запустить frontend

**Терминал 5:**

```powershell
cd C:\Users\stark\Documents\recipe-manager\frontend
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1
```

Открой `http://127.0.0.1:5173` и войди как пользователь A.

### Шаг 7. Создать import

1. Открой import form.
2. Добавь оба тестовых изображения.
3. Добавь текст:

```text
Название: Тестовый горячий бутерброд.
Ингредиенты: хлеб, сыр.
Инструкция: положить сыр на хлеб и запечь до расплавления.
```

4. Отправь import.
5. Дождись terminal success.
6. Запиши import detail URL и recipe ID.
7. Не перезапускай backend.

Если внешний AI provider мешает smoke, используй поддерживаемый fake/auto provider согласно текущей документации и начни PREVIEW заново.

### Шаг 8. Проверить UI

Проверь:

- recipe list показывает cover;
- recipe detail показывает hero cover;
- cover options показывают оба изображения;
- source-image modal открывается;
- import detail показывает submitted images;
- переходы и закрытие modal не дают ошибок Console;
- default SVG работает, когда media reference отсутствует.

### Шаг 9. Проверить protocol в DevTools

1. DevTools → Network → Preserve log.
2. Очисти requests.
3. Открой recipe detail.
4. Фильтр `media`.
5. Найди `POST /media/access`.
6. В Payload проверь несколько `{type, id}` items и отсутствие storage key.
7. В Response проверь `accessMode: "authenticated_fetch"`, `expiresAt: null` и URL `/media/recipe_image/<id>` либо `/media/import_source_image/<id>`.
8. Убедись, что URL не содержит storage prefixes, owner ID, bucket name или filename.
9. Найди следующий GET.
10. Проверь `Authorization: Bearer ...` и корректный image content type.

Не копируй bearer token в PR или чат.

### Шаг 10. Проверить partial success

1. В Network выбери успешный `POST /media/access`.
2. Copy → Copy as fetch.
3. В Console измени body: один существующий item и второй item того же type с `id: "missing-p10-media-id"`.
4. Выполни fetch и прочитай JSON.

Ожидается HTTP `200`, grant для существующего item и `MEDIA_NOT_FOUND` для missing item.

### Шаг 11. Проверить GET без auth

Скопируй URL `/media/{media_type}/{media_id}` и открой в Incognito без Clerk session.

Ожидается `401`/`403` или equivalent gateway auth error. Файл не открывается.

### Шаг 12. Проверить foreign ID

Если есть пользователь B:

1. сохрани type/ID пользователя A;
2. войди как B в другом browser profile;
3. скопируй authenticated request как fetch;
4. отправь `POST /media/access` с reference пользователя A.

Ожидается тот же `MEDIA_NOT_FOUND`, что для missing ID.

Если пользователя B нет, отметь live foreign-user smoke как не выполненный; automated evidence остаётся обязательным.

### Шаг 13. Что не нужно делать вручную

Не меняй БД ради inactive recipe, detached image, resource `DELETED`, non-image source, null key, `FAILED`/`FAILED_ARTIFACTS_REMOVED`, duplicate positions, query count, Blob URL cleanup, direct expiry refresh, no-HEAD или provider `503`. Это проверяет Codex тестами.

### Шаг 14. Остановить окружение

В frontend/backend/worker terminals нажми `Ctrl+C`, затем:

```powershell
cd C:\Users\stark\Documents\recipe-manager
docker compose stop krakend adminer redis postgres
```

Не используй `docker compose down -v`, если не собираешься удалить локальные volumes.

## 6. Ручная S3 проверка

Выполняй только с private test bucket.

Проверь:

- owned media получает `direct`;
- `expiresAt` примерно через 60 секунд;
- браузер грузит bytes напрямую из S3;
- backend не проксирует файл;
- URL/signature отсутствуют в logs;
- missing/foreign одинаковы;
- bucket/storage key отсутствуют в domain API;
- после expiry нужен новый grant;
- DB reference на отсутствующий object получает signed URL, а S3 GET возвращает `404`;
- access flow не вызывает `HeadObject`.

Если smoke не выполнялся, PR должен явно содержать verification gap.

## 7. Merge blockers

Не мержи, если:

- automated checks не зелёные;
- correctness/security manual gap не закрыт;
- legacy endpoint сохранён;
- storage keys или `mediaUrl` выходят наружу;
- missing/foreign различимы;
- presigned URL логируется;
- есть HEAD-per-grant;
- ownership находится в route/provider;
- upload scope добавлен;
- frontend использует URL-shape logic;
- Codex не предоставил self-audit и key human-review map.

## 8. После review

- переведи draft PR в ready только после проверки;
- смержи выбранным способом;
- обнови локальный `main`;
- проверь roadmap/docs;
- удали implementation branch после merge;
- зафиксируй фактические automated и manual results;
- следующую фазу обсуждай отдельно.