# Recipe Manager

Greenfield rewrite of the recipe MVP with a FastAPI backend and React/Vite frontend.

## Backend

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

Preview mode uses separate local storage and clears preview data on restart:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
$env:APP_ENV="preview"; uv run fastapi dev app/main.py --host 127.0.0.1 --port 8010
```

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

The persistent dev SQLite database lives here after the backend starts:

```text
C:\Users\stark\Documents\recipe-manager\backend\storage\dev\app.db
```

Browser dashboard:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv run sqlite_web storage\dev\app.db --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080`.

Preview mode uses a separate database at `backend\storage\preview\app.db` and
clears it on backend restart.

Current import processing is sync-first: `POST /imports` creates an `ImportJob`,
processes it immediately, and the frontend still polls `GET /imports/{jobId}` so
the contract can move to a real background queue later.

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
