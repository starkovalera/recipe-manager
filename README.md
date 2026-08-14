# Recipe Manager

Greenfield recipe manager with a FastAPI backend, React/Vite frontend, PostgreSQL, Redis/Dramatiq background work, and KrakenD/Clerk authentication.

The canonical authentication design is in [`docs/authentication-and-authorization.md`](docs/authentication-and-authorization.md). Manual lifecycle checks are in [`docs/manual-testing/clerk-lifecycle.md`](docs/manual-testing/clerk-lifecycle.md).

## Project Planning

Use the human-facing [`Project Roadmap`](docs/roadmap.md) for the project-scale Design and Development work graph, release outcomes, target architecture link, and links to the main project documents. Detailed Design scope lives in [`design/roadmap.md`](design/roadmap.md); detailed Development phases live in [`docs/architecture/production-roadmap.md`](docs/architecture/production-roadmap.md). Superseded plans are preserved under [`docs/archive/`](docs/archive/README.md); Future Capabilities are refined under [`docs/future/`](docs/future/README.md).

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

### Local Clerk development sign-in

The seeded `+clerk_test` users use Clerk's fixed development email-code flow. Do not use the password flow: Clerk may reject the seed password as compromised. In the sign-in dialog:

1. Enter the email from `backend/config/preview-users.local.toml` and select **Continue**.
2. Select **Email code to …**.
3. Enter `424242`.
4. Wait for the application home page and the first `POST /me/provision` request before testing protected routes.

The `424242` code is only for Clerk development test users and must not be used for non-test accounts.

## Authentication Operations

The frontend obtains Clerk tokens in memory. KrakenD validates each protected request and forwards only the verified subject. FastAPI resolves that subject to an internal active user and remains authoritative for fixed roles, capabilities, and owner scoping.

The first request after a Clerk session is established is `POST /me/provision`. Clerk webhooks reconcile `user.created`, `user.updated`, and `user.deleted`; webhook delivery is not a synchronous login dependency.

For local webhooks, expose the webhook ingress through a public tunnel and configure the exact HTTPS URL in Clerk. Clerk cannot deliver directly to localhost. The FastAPI endpoint is `POST /webhooks/clerk` and verifies Svix signatures.

After a worker or publish outage, dispatch the oldest bounded batch of pending transactional outbox messages with:

```powershell
cd C:\Users\stark\Documents\recipe-manager\backend
uv run python -m app.queueing.reconcile_outbox
```

Exit code `0` means every message in the processed batch dispatched successfully. Exit code `1` means at least one message failed and remains pending. This is manual PREVIEW recovery until scheduled maintenance dispatch is implemented.

The separate account-deletion domain recovery command scans every current `DELETION_PENDING` user, creates a new durable deletion intent for each, and attempts immediate dispatch:

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

| Mode | Database | Queue provider | Storage provider | Redis | Upload directory |
| --- | --- | --- | --- | --- | --- |
| `DEV` | Local PostgreSQL default | `DRAMATIQ` | `LOCAL` | Local default | Local persistent default |
| `PREVIEW` | Local PostgreSQL default | `DRAMATIQ` | `LOCAL` | Local default | Local resettable default |
| `TEST` | Isolated SQLite default | `DRAMATIQ` test-safe configuration | `LOCAL` | No running server required | Isolated test default |
| `PROD` | Explicit PostgreSQL required | Explicit `SQS` required | Explicit `S3` required | Not supported | Not supported |

Production settings fail closed instead of falling back to SQLite, Redis/Dramatiq, or local media storage. The P4 SQS publisher, P9 S3 storage adapter, and P10 private-media access boundary are implemented. SQS requires an explicit AWS region and dedicated queue URLs; S3 requires the region and `S3_USER_MEDIA_BUCKET_NAME`. Adapter construction performs no AWS call, credentials come from the standard boto3 credential chain, and application code does not provision AWS resources. Browsers request grants for stable media IDs; S3 uses 60-second presigned GETs and LOCAL uses an authenticated domain-ID route. See [`docs/media-access.md`](docs/media-access.md).

`POST /imports` creates a queued `ImportJob` and returns `202 Accepted`. The frontend remains on the import form, polls notifications, and can submit additional imports within concurrency limits.

## LocalStack S3 Verification

LocalStack provides an opt-in disposable S3 environment for testing storage and direct presigned media access without an AWS account. Normal `DEV` and `PREVIEW` startup continues to use `LOCAL` storage unless explicitly overridden.

Add these non-secret overrides to ignored `backend/.env`:

```dotenv
APP_ENV=PREVIEW
STORAGE_PROVIDER=S3
AWS_REGION=us-east-1
AWS_ENDPOINT_URL_S3=http://s3.localhost.localstack.cloud:4566
S3_USER_MEDIA_BUCKET_NAME=recipe-manager-local-user-media
S3_SYSTEM_ARTIFACTS_BUCKET_NAME=recipe-manager-local-system-artifacts
```

Start the opt-in LocalStack service alongside the normal infrastructure:

```powershell
docker compose --profile local-s3 up -d postgres redis adminer krakend localstack
docker compose --profile local-s3 ps localstack
```

LocalStack test credentials use boto3's standard credential chain. Set them in every terminal that runs an S3 client, including FastAPI, Dramatiq, and opt-in integration tests:

```powershell
$env:AWS_ACCESS_KEY_ID="test"
$env:AWS_SECRET_ACCESS_KEY="test"
```

Inspect stored objects:

```powershell
docker compose --profile local-s3 exec localstack awslocal s3 ls s3://recipe-manager-local-user-media --recursive
docker compose --profile local-s3 logs -f localstack
```

Run the repeatable LocalStack integration suite:

```powershell
cd backend
New-Item -ItemType Directory -Force .pytest-tmp | Out-Null
$env:AWS_ACCESS_KEY_ID="test"
$env:AWS_SECRET_ACCESS_KEY="test"
$env:RUN_LOCALSTACK_INTEGRATION="1"
uv run pytest tests/integration/localstack/test_s3_media_flow.py -q --basetemp=.pytest-tmp/localstack-integration
```

LocalStack has no persistent volume in this profile. Recreate only that service to reset both local buckets without touching PostgreSQL, Redis, or KrakenD:

```powershell
docker compose --profile local-s3 rm -sf localstack
docker compose --profile local-s3 up -d localstack
```

PREVIEW database reset and LocalStack reset are separate operations. After changing storage settings, restart both FastAPI and Dramatiq so they use the same provider and endpoint. See [`docs/handoffs/p10-presigned-media-access-owner-runbook.md`](docs/handoffs/p10-presigned-media-access-owner-runbook.md) for the browser checks and the separate live-AWS verification scope.

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
