# Recipe Manager

Greenfield rewrite of the recipe MVP with a FastAPI backend and React/Vite frontend.

## Backend

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv sync
uv run fastapi dev app/main.py
```

Preview mode uses separate local storage and clears preview data on restart:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
$env:APP_ENV="preview"; uv run fastapi dev app/main.py
```

## Frontend

```powershell
cd C:\Users\stark\Documents\recipe-manager\frontend
pnpm install
pnpm dev
```

Set `VITE_API_BASE_URL` if the backend is not running at `http://localhost:8000`.

Current import processing is sync-first: `POST /imports` creates an `ImportJob`,
processes it immediately, and the frontend still polls `GET /imports/{jobId}` so
the contract can move to a real background queue later.
