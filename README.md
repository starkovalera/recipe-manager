# Recipe Manager

Greenfield rewrite of the recipe MVP with a FastAPI backend and React/Vite frontend.

## Backend

Start local infrastructure first:

```powershell
cd C:\Users\stark\Documents\recipe-manager
docker compose up -d postgres redis
```

Put your AI key in `backend/.env`:

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=<your-openai-key>
```

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv sync
uv run fastapi dev app/main.py --host 127.0.0.1 --port 8010
```

Start the import worker in a second backend terminal:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv run dramatiq app.imports.tasks
```

Preview mode uses separate local storage and clears preview data on restart:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
$env:APP_ENV="preview"; uv run fastapi dev app/main.py --host 127.0.0.1 --port 8010
```

`dev` uses PostgreSQL database `recipe_manager_dev`. `preview` uses
`recipe_manager_preview` and resets that schema plus local preview uploads on
backend startup.

`POST /imports` now creates a queued import job and enqueues Dramatiq work. The
worker process must be running for imports to finish. Frontend polling and
notification UX are still Phase 1d.

## Frontend

Frontend API URL is in `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8010
VITE_DEBUG_API=true
```

```powershell
cd C:\Users\stark\Documents\recipe-manager\frontend
pnpm install
pnpm dev
```

Set `VITE_API_BASE_URL` if the backend is not running at `http://127.0.0.1:8010`.

## Database Dashboard

The normal dev database is PostgreSQL:

```dotenv
postgresql+psycopg://recipe_manager:recipe_manager@127.0.0.1:5432/recipe_manager_dev
```

Adminer is included in Docker Compose:

```powershell
cd C:\Users\stark\Documents\recipe-manager
docker compose up -d postgres redis adminer
```

Open `http://127.0.0.1:8080` and use:

```text
System: PostgreSQL
Server: postgres
Username: recipe_manager
Password: recipe_manager
Database: recipe_manager_dev
```

For preview data, use the same values but set:

```text
Database: recipe_manager_preview
```

From desktop PostgreSQL GUIs, for example DBeaver, DataGrip, TablePlus, or pgAdmin, use:

```text
host: 127.0.0.1
port: 5432
database: recipe_manager_dev
user: recipe_manager
password: recipe_manager
```

Use `database: recipe_manager_preview` for preview.

The old SQLite dashboard command is only useful for test/smoke databases and should use another port if Adminer is running:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv run sqlite_web storage\dev\app.db --host 127.0.0.1 --port 8081
```

Open `http://127.0.0.1:8081` when using a SQLite database explicitly.

Current import processing is background-first: `POST /imports` creates an
`ImportJob(status=queued)`, records job events and notifications, enqueues
Dramatiq work, and returns `202 Accepted`. The worker records completion status
and the frontend can poll `GET /imports/{jobId}`.

## Logs

Backend import logs are printed in the backend terminal:

```text
[recipes.import] AI provider selected
[recipes.import] Import job created
[recipes.import] AI extraction quality
[recipes.import] Import job succeeded
```

Frontend API logs are printed in the browser console and, in Vite dev mode, also
mirrored to the frontend terminal when `VITE_DEBUG_API=true`:

```text
[recipes.frontend.api] request
[recipes.frontend.api] response
[recipes.frontend.api] error
```
