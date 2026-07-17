# Recipe Manager

Greenfield recipe manager with a FastAPI backend, React/Vite frontend, PostgreSQL, Redis/Dramatiq background work, and KrakenD/Clerk authentication.

The canonical authentication design is in [`docs/authentication-and-authorization.md`](docs/authentication-and-authorization.md). Manual lifecycle checks are in [`docs/manual-testing/clerk-lifecycle.md`](docs/manual-testing/clerk-lifecycle.md).

## Repository Workflow

`main` is the default integration branch. Feature changes are submitted through pull requests, and the required backend, frontend, and gateway checks must pass before merge.

## Local Configuration

Authentication is required in both `dev` and `preview`. Configure a Clerk development instance and enable Restricted mode when registration must be invite-only.

Create ignored local env files from the committed examples:

```text
.env                  KrakenD issuer and JWKS URL
backend/.env          backend secret key, webhook secret, runtime settings
frontend/.env         publishable key and gateway API URL
```

Minimum root `.env`:

```dotenv
CLERK_ISSUER=https://<instance>.clerk.accounts.dev
CLERK_JWKS_URL=https://<instance>.clerk.accounts.dev/.well-known/jwks.json
```

Minimum Clerk values in `backend/.env`:

```dotenv
CLERK_SECRET_KEY=sk_test_...
CLERK_WEBHOOK_SIGNING_SECRET=whsec_...
CLERK_API_URL=https://api.clerk.com
FRONTEND_INVITATION_URL=http://127.0.0.1:5173/sign-up
```

Minimum `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8081
VITE_DEBUG_API=true
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
```

`CLERK_SECRET_KEY` and `CLERK_WEBHOOK_SIGNING_SECRET` are secrets. Do not commit local env files.

The Clerk CLI can link the project and pull development keys:

```powershell
clerk auth login
clerk link
clerk env pull
```

Review pulled values and place them in the appropriate ignored env files above.

## Local Startup

### Terminal 1 - Infrastructure and Gateway

```powershell
cd C:\Users\stark\Documents\recipe-manager
docker compose up -d --build postgres redis adminer krakend
```

### Terminal 2 - FastAPI Upstream

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv sync
uv run fastapi dev app/main.py --host 127.0.0.1 --port 8010
```

If `backend/.env` contains `APP_ENV=PREVIEW`, no shell override is needed. Preview startup recreates the preview schema and upload directory. Otherwise, a one-command override is:

```powershell
$env:APP_ENV="PREVIEW"; uv run fastapi dev app/main.py --host 127.0.0.1 --port 8010
```

### Terminal 3 - Worker

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv run dramatiq app.worker
```

The worker is required for imports, embeddings, and account deletion.

### Terminal 4 - Frontend

```powershell
cd C:\Users\stark\Documents\recipe-manager\frontend
pnpm install
pnpm dev
```

Open `http://127.0.0.1:5173`. Browser API and media requests go to KrakenD on `8081`, which forwards verified requests to FastAPI on `8010`.

## Preview User Bootstrap

Preview does not bypass Clerk. To seed a known Clerk development user with exact local roles:

1. Copy `backend/config/preview-users.example.toml` to the ignored `backend/config/preview-users.local.toml`.
2. Replace `auth_user_id` and email with a real Clerk development user.
3. Start FastAPI and wait for preview migrations to complete.
4. Run:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv run python -m app.local.seed_preview_users
```

Ordinary first-login provisioning creates an active user, `UserSettings`, and default tags without privileged roles.

## Authentication Operations

The frontend obtains Clerk tokens in memory. KrakenD validates each protected request and forwards only the verified subject. FastAPI resolves that subject to an internal active user and remains authoritative for fixed roles, capabilities, and owner scoping.

The first request after a Clerk session is established is `POST /me/provision`. Clerk webhooks reconcile `user.created`, `user.updated`, and `user.deleted`; webhook delivery is not a synchronous login dependency.

For local webhooks, expose the webhook ingress through a public tunnel and configure the exact HTTPS URL in Clerk. Clerk cannot deliver directly to localhost. The FastAPI endpoint is `POST /webhooks/clerk` and verifies Svix signatures.

After a worker or publish outage, republish durable pending account deletions with:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv run python -m app.users.reconcile_deletions
```

## Gateway Diagnostics

```powershell
curl.exe http://127.0.0.1:8081/__health
curl.exe http://127.0.0.1:8081/health
docker compose logs -f krakend
docker compose build krakend
```

`/__health` checks KrakenD itself. `/health` is proxied to FastAPI and fails when the upstream is unavailable.

Direct FastAPI access at `http://127.0.0.1:8010` is upstream diagnostics only. It bypasses JWT validation, so protected direct requests require a manually supplied trusted subject header and do not represent the production trust boundary.

## Runtime Modes

`dev` uses PostgreSQL database `recipe_manager_dev` and persistent media under `backend/storage/dev/uploads`.

`preview` uses `recipe_manager_preview` and resets that schema plus `backend/storage/preview/uploads` on backend startup.

`POST /imports` creates a queued `ImportJob` and returns `202 Accepted`. The frontend remains on the import form, polls notifications, and can submit additional imports within concurrency limits.

Without an OpenAI key, recipe extraction and embeddings use local fake providers. To use OpenAI, set in `backend/.env`:

```dotenv
AI_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=<your-openai-key>
```

## Database Dashboard

Adminer runs at `http://127.0.0.1:8080` when started through Compose.

```text
System: PostgreSQL
Server: postgres
Username: recipe_manager
Password: recipe_manager
Database: recipe_manager_dev
```

Use `recipe_manager_preview` for preview data.

Desktop PostgreSQL clients use:

```text
host: 127.0.0.1
port: 5432
database: recipe_manager_dev or recipe_manager_preview
user: recipe_manager
password: recipe_manager
```

## Logs

Backend import logs are printed in the backend and worker terminals with structured context. Typical lifecycle messages include:

```text
Import job created.
Extractor selected.
Extraction finished.
Import job succeeded.
```

Frontend API logs are printed in the browser console and mirrored to the Vite terminal in development when `VITE_DEBUG_API=true`:

```text
[recipes.frontend.api] request
[recipes.frontend.api] response
[recipes.frontend.api] error
```

## Verification

Backend:

```powershell
cd backend
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Frontend:

```powershell
cd frontend
pnpm exec vitest run
pnpm run typecheck
pnpm run build
```
