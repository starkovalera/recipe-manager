# Recipe Manager

Greenfield rewrite of the recipe MVP with a FastAPI backend and React/Vite frontend.

## Backend

```powershell
cd backend
uv sync
uv run fastapi dev app/main.py
```

Preview mode uses separate local storage and clears preview data on restart:

```powershell
cd backend
$env:APP_ENV="preview"; uv run fastapi dev app/main.py
```

## Frontend

```powershell
cd frontend
pnpm install
pnpm dev
```
