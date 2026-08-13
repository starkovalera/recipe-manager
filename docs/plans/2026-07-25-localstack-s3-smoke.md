# LocalStack S3 Smoke Testing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in local S3 environment that exercises the existing storage and presigned-media flows through LocalStack without requiring an AWS account or weakening production configuration.

**Architecture:** LocalStack runs as an optional Docker Compose service and exposes its S3 endpoint to the host-running backend, worker, and browser. The application keeps using the existing `S3StorageService` and `S3DownloadAccessProvider`; a single optional endpoint setting is passed to both adapters, while PROD rejects any custom S3 endpoint. LocalStack initializes two private test buckets and CORS rules, and the existing P10 owner runbook gains a reproducible local-S3 section.

**Tech Stack:** Docker Compose, LocalStack S3, boto3/botocore, FastAPI/Pydantic Settings, PowerShell, pytest.

## Global Constraints

- LocalStack is opt-in and must not change normal LOCAL/PREVIEW startup defaults.
- `APP_ENV=PROD` must reject a custom S3 endpoint.
- Real AWS credentials and bucket names must never be committed.
- LocalStack credentials are fixed test values and must be supplied through the standard boto3 credential chain.
- Both storage writes and presigned downloads must use the same configured S3 endpoint.
- The application must not add `HeadObject` to the media-access flow.
- The ordinary backend, frontend, and gateway test suites must not require LocalStack.
- The browser-facing presigned URL must resolve from the Windows host; do not generate a Docker-internal hostname such as `localstack:4566`.
- Existing S3 key formats, stable media references, 60-second grants, ownership checks, and partial-success behavior remain unchanged.

---

## File Map

- Modify `backend/app/core/config.py`: declare and validate the optional custom S3 endpoint.
- Modify `backend/app/storage/s3.py`: pass the configured endpoint to the lazy boto3 S3 client.
- Modify `backend/app/storage/runtime.py`: propagate the endpoint to storage.
- Modify `backend/app/media/access/s3.py`: pass the same endpoint to the lazy presigning client.
- Modify `backend/app/media/access/runtime.py`: propagate the endpoint to media access.
- Modify `backend/tests/core/test_config.py`: cover PREVIEW acceptance and PROD rejection.
- Modify `backend/tests/storage/test_runtime.py`: verify endpoint propagation to storage.
- Modify `backend/tests/storage/test_s3.py`: verify lazy client construction with the endpoint.
- Modify `backend/tests/media/test_access_providers.py`: verify lazy presigning client construction with the endpoint.
- Modify `docker-compose.yml`: add the opt-in LocalStack S3 service and health check.
- Create `docker/localstack/init/01-create-s3-buckets.sh`: create both buckets and configure browser CORS idempotently.
- Create `backend/tests/integration/localstack/test_s3_media_flow.py`: provide repeatable opt-in LocalStack storage, presigning, missing-object, and expiry checks.
- Modify `backend/.env.example`: document local-S3 overrides without adding credentials.
- Modify `README.md`: document startup and reset commands.
- Modify `docs/handoffs/p10-presigned-media-access-owner-runbook.md`: add the complete local-S3 verification procedure and distinguish it from live AWS verification.

---

### Task 1: Add a fail-closed custom S3 endpoint setting

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/tests/core/test_config.py`

**Interfaces:**
- Produces: `Settings.aws_endpoint_url_s3: str | None`
- Constraint: accepted in `DEV`, `PREVIEW`, and `TEST`; rejected in `PROD` when non-empty.

- [ ] **Step 1: Add failing settings tests**

Add tests that construct PREVIEW S3 settings with:

```python
aws_endpoint_url_s3="http://s3.localhost.localstack.cloud:4566"
```

and assert that the value is retained. Add a PROD test that passes the same value to `build_sqs_settings()` and expects a `ValidationError` mentioning `AWS_ENDPOINT_URL_S3` and `PROD`.

- [ ] **Step 2: Isolate the test process from the endpoint environment variable**

Add `AWS_ENDPOINT_URL_S3` to the autouse environment cleanup fixture in `backend/tests/core/test_config.py` so a developer's LocalStack shell does not affect tests.

- [ ] **Step 3: Run the focused test and confirm failure**

```powershell
cd backend
uv run pytest tests/core/test_config.py -q
```

Expected: the new tests fail because the field and PROD rule do not exist.

- [ ] **Step 4: Add the setting and validation**

Add:

```python
aws_endpoint_url_s3: str | None = None
```

Include it in blank-string normalization. In the environment validator reject a non-null value when `app_env is AppEnv.PROD`:

```python
if self.app_env is AppEnv.PROD and self.aws_endpoint_url_s3:
    raise ValueError("AWS_ENDPOINT_URL_S3 is not supported in PROD.")
```

Do not add access-key or secret-key fields to `Settings`.

- [ ] **Step 5: Run the focused settings tests**

```powershell
cd backend
uv run pytest tests/core/test_config.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the configuration boundary**

```powershell
git add backend/app/core/config.py backend/tests/core/test_config.py
git commit -m "feat: support local s3 endpoint configuration"
```

---

### Task 2: Propagate one endpoint to both S3 adapters

**Files:**
- Modify: `backend/app/storage/s3.py`
- Modify: `backend/app/storage/runtime.py`
- Modify: `backend/app/media/access/s3.py`
- Modify: `backend/app/media/access/runtime.py`
- Modify: `backend/tests/storage/test_runtime.py`
- Modify: `backend/tests/storage/test_s3.py`
- Modify: `backend/tests/media/test_access_providers.py`

**Interfaces:**
- Consumes: `Settings.aws_endpoint_url_s3`
- Produces: optional `endpoint_url` constructor parameter on `S3StorageService` and `S3DownloadAccessProvider`.

- [ ] **Step 1: Add failing lazy-client tests**

Extend the existing boto3 factory assertions so configured adapters call:

```python
boto3.client(
    "s3",
    region_name="us-east-1",
    endpoint_url="http://s3.localhost.localstack.cloud:4566",
)
```

Retain coverage that client construction is lazy and the client is reused.

- [ ] **Step 2: Add failing runtime propagation tests**

Build PREVIEW S3 settings with the LocalStack endpoint, patch the adapter constructors, invoke `get_storage_service(settings)` and `get_download_access_provider(settings)`, and assert both receive the same endpoint.

- [ ] **Step 3: Run the focused adapter tests and confirm failure**

```powershell
cd backend
uv run pytest tests/storage/test_runtime.py tests/storage/test_s3.py tests/media/test_access_providers.py -q
```

Expected: the new endpoint assertions fail.

- [ ] **Step 4: Implement endpoint propagation**

Add `endpoint_url: str | None = None` to both S3 adapter constructors, store it, and pass it when lazily constructing each boto3 client. Runtime factories pass `resolved_settings.aws_endpoint_url_s3` to their adapter.

Do not add a new one-call S3 client factory. The existing storage and download adapters retain responsibility for their own lazy clients.

- [ ] **Step 5: Run the focused adapter tests**

```powershell
cd backend
uv run pytest tests/storage/test_runtime.py tests/storage/test_s3.py tests/media/test_access_providers.py -q
```

Expected: PASS.

- [ ] **Step 6: Run the infrastructure boundary test**

```powershell
cd backend
uv run pytest tests/infra/test_queue_publishing_boundary.py tests/infra/test_storage_transaction_boundaries.py -q
```

Expected: PASS; no boto3 use leaks into application/domain modules.

- [ ] **Step 7: Commit adapter support**

```powershell
git add backend/app/storage backend/app/media/access backend/tests/storage backend/tests/media
git commit -m "feat: route s3 adapters through configured endpoint"
```

---

### Task 3: Add an opt-in LocalStack S3 service

**Files:**
- Modify: `docker-compose.yml`
- Create: `docker/localstack/init/01-create-s3-buckets.sh`

**Interfaces:**
- Produces: Compose service `localstack` under profile `local-s3`.
- Produces buckets: `recipe-manager-local-user-media` and `recipe-manager-local-system-artifacts`.

- [ ] **Step 1: Add the LocalStack service**

Use a pinned LocalStack image rather than `latest`. Configure:

```yaml
profiles: ["local-s3"]
ports:
  - "127.0.0.1:4566:4566"
environment:
  SERVICES: s3
  AWS_DEFAULT_REGION: us-east-1
  AWS_ACCESS_KEY_ID: test
  AWS_SECRET_ACCESS_KEY: test
  S3_SKIP_SIGNATURE_VALIDATION: "0"
  S3_USER_MEDIA_BUCKET_NAME: recipe-manager-local-user-media
  S3_SYSTEM_ARTIFACTS_BUCKET_NAME: recipe-manager-local-system-artifacts
```

Mount `docker/localstack/init/01-create-s3-buckets.sh` into `/etc/localstack/init/ready.d/`. Add a health check against `/_localstack/health` that verifies S3 is available.

Do not add a persistent volume in this first version. The environment is intentionally disposable, and recreating the container resets local S3 state.

`S3_SKIP_SIGNATURE_VALIDATION=0` is required so the expiry integration test exercises signed URL validation rather than LocalStack's permissive default.

- [ ] **Step 2: Create the idempotent initialization script**

The script must use `awslocal s3api head-bucket` before `create-bucket`, create both configured buckets, and apply CORS to the user-media bucket for:

```json
{
  "AllowedOrigins": ["http://127.0.0.1:5173", "http://localhost:5173"],
  "AllowedMethods": ["GET"],
  "AllowedHeaders": ["*"],
  "ExposeHeaders": ["ETag", "Content-Type"],
  "MaxAgeSeconds": 300
}
```

Do not make either bucket public.

- [ ] **Step 3: Validate Compose rendering**

```powershell
docker compose --profile local-s3 config
```

Expected: exit code `0`; no missing environment interpolation and only loopback port exposure for LocalStack.

- [ ] **Step 4: Start LocalStack and verify initialization**

```powershell
docker compose --profile local-s3 up -d localstack
docker compose --profile local-s3 ps localstack
docker compose --profile local-s3 exec localstack awslocal s3api list-buckets
```

Expected: healthy service and both local bucket names in the response.

- [ ] **Step 5: Verify the buckets remain private**

```powershell
docker compose --profile local-s3 exec localstack awslocal s3api get-public-access-block --bucket recipe-manager-local-user-media
```

If LocalStack does not synthesize a public-access-block response for a newly created bucket, verify instead that there is no bucket policy or public ACL. Record the emulator limitation in the runbook; do not add a public policy to make the check pass.

- [ ] **Step 6: Commit LocalStack infrastructure**

```powershell
git add docker-compose.yml docker/localstack/init/01-create-s3-buckets.sh
git commit -m "infra: add localstack s3 profile"
```

---

### Task 4: Document local-S3 configuration and lifecycle

**Files:**
- Modify: `backend/.env.example`
- Modify: `README.md`
- Modify: `docs/handoffs/p10-presigned-media-access-owner-runbook.md`

**Interfaces:**
- Produces: exact operator commands for startup, inspection, and reset.

- [ ] **Step 1: Document non-secret backend overrides**

Add a LOCALSTACK/PREVIEW example without credentials:

```dotenv
APP_ENV=PREVIEW
STORAGE_PROVIDER=S3
AWS_REGION=us-east-1
AWS_ENDPOINT_URL_S3=http://s3.localhost.localstack.cloud:4566
S3_USER_MEDIA_BUCKET_NAME=recipe-manager-local-user-media
S3_SYSTEM_ARTIFACTS_BUCKET_NAME=recipe-manager-local-system-artifacts
```

State explicitly that `AWS_ACCESS_KEY_ID=test` and `AWS_SECRET_ACCESS_KEY=test` must be process environment variables or a local AWS profile, not application settings.

- [ ] **Step 2: Document the Windows startup sequence**

Infrastructure terminal:

```powershell
docker compose --profile local-s3 up -d postgres redis adminer krakend localstack
```

Backend and worker terminals must each receive:

```powershell
$env:AWS_ACCESS_KEY_ID="test"
$env:AWS_SECRET_ACCESS_KEY="test"
```

The backend settings come from ignored `backend/.env`; the worker must run from the same backend directory.

- [ ] **Step 3: Document reset and inspection commands**

Inspection:

```powershell
docker compose --profile local-s3 exec localstack awslocal s3 ls s3://recipe-manager-local-user-media --recursive
docker compose --profile local-s3 logs -f localstack
```

Reset only LocalStack S3:

```powershell
docker compose --profile local-s3 rm -sf localstack
docker compose --profile local-s3 up -d localstack
```

State that PREVIEW database reset and LocalStack reset are separate operations.

- [ ] **Step 4: Add a LocalStack section to the P10 runbook**

Keep the existing LOCAL/PREVIEW and Live S3 sections. Insert LocalStack as an intermediate test tier and clearly state which production claims it cannot validate: real IAM permissions, AWS Block Public Access enforcement, CloudTrail evidence, AWS networking/TLS, and exact real-S3 missing-object authorization behavior.

- [ ] **Step 5: Validate documentation commands against Compose**

Run each non-destructive command from the repository root and correct any Windows/Compose mismatch.

- [ ] **Step 6: Commit documentation**

```powershell
git add backend/.env.example README.md docs/handoffs/p10-presigned-media-access-owner-runbook.md
git commit -m "docs: add localstack s3 verification workflow"
```

---

### Task 5: Execute the automated and manual smoke checks

**Files:**
- Create: `backend/tests/integration/localstack/test_s3_media_flow.py`
- Modify only if a discovered defect requires a separately reviewed fix.

**Interfaces:**
- Consumes: LocalStack profile, P10 media API, existing Clerk/KrakenD PREVIEW stack.
- Produces: recorded verification evidence in the PR description or owner-runbook completion note.

- [ ] **Step 1: Run backend checks without LocalStack**

Create an opt-in module guarded by `RUN_LOCALSTACK_INTEGRATION=1`. It must cover
storage save/list/read/delete, a direct presigned GET with the expected bytes and
60-second metadata, a missing object that still receives a grant without a
preflight lookup, and signature expiry using a shortened test-only TTL.

Without the flag, the module must skip and the ordinary suite must not contact
LocalStack.

Then run backend checks without LocalStack:

```powershell
cd backend
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Expected: normal CI-style backend checks pass without a running LocalStack container.

- [ ] **Step 2: Run frontend and gateway checks**

```powershell
cd frontend
pnpm exec vitest run
pnpm run typecheck
pnpm run build
```

Then run the repository's existing KrakenD validation command documented by the current gateway test setup.

- [ ] **Step 3: Start the complete PREVIEW + LocalStack stack**

Start PostgreSQL, Redis, Adminer, KrakenD, LocalStack, FastAPI, Dramatiq, and Vite using the documented commands. Confirm KrakenD `/__health`, backend `/health`, LocalStack health, and frontend sign-in before testing imports.

- [ ] **Step 4: Create fresh S3-backed data**

Import a new image or supported URL after S3 mode is active. Do not use recipes created under LOCAL storage, because their database keys may exist while the corresponding LocalStack objects do not.

Verify the canonical object key appears under the user-media bucket:

```powershell
docker compose --profile local-s3 exec localstack awslocal s3 ls s3://recipe-manager-local-user-media --recursive
```

- [ ] **Step 5: Verify the grant contract**

In browser Network, inspect successful `POST /media/access`:

- HTTP `200`;
- `accessMode` is `direct`;
- `expiresAt` is approximately 60 seconds after response time;
- grant URL targets LocalStack on port `4566`;
- response contains no bucket name or storage key outside the signed URL;
- the recipe/media domain responses expose stable IDs rather than storage keys.

- [ ] **Step 6: Verify direct browser retrieval**

Open the presigned request in Network and confirm its remote address is LocalStack `:4566`, not KrakenD `:8081` or FastAPI `:8010`. Confirm the expected MIME type and bytes are returned.

- [ ] **Step 7: Verify partial success and normalized authorization failures**

Request one owned stable media ID plus `missing-p10-media-id`. Confirm HTTP `200`, one grant, and one `MEDIA_NOT_FOUND`. Repeat with a known foreign ID and confirm its item is indistinguishable from the missing-ID item.

- [ ] **Step 8: Verify expiry**

Save one signed URL, wait more than 60 seconds, and request it again. Confirm the old URL is rejected. Request a fresh grant through `/media/access` and confirm the new URL retrieves the bytes.

- [ ] **Step 9: Verify a dangling DB reference**

Delete an object's bytes through `awslocal` while leaving its owned database row intact. Request `/media/access` and confirm it still returns a direct signed grant without `HeadObject`; requesting that URL from LocalStack returns the emulator's missing-object response.

- [ ] **Step 10: Inspect logs**

Search backend, worker, KrakenD, and LocalStack logs. Confirm backend/application logs contain no full presigned URL, signature, bucket name, or storage key. Confirm LocalStack records direct GETs and no application-triggered `HeadObject` for grant creation.

- [ ] **Step 11: Reset disposable state**

Recreate the LocalStack container and restart PREVIEW when a clean database is required. Confirm the two bucket initialization hook runs successfully after recreation.

- [ ] **Step 12: Record evidence and remaining live-AWS gap**

Record exact check totals and manual outcomes. Mark LocalStack functional verification complete, but leave live AWS IAM/Block Public Access/CloudTrail verification open until tested against a private AWS bucket.

---

## Acceptance Checklist

- [ ] LocalStack is opt-in and normal PREVIEW remains `LOCAL` storage by default.
- [ ] Both application S3 clients use the same custom endpoint.
- [ ] PROD rejects `AWS_ENDPOINT_URL_S3`.
- [ ] No AWS credential fields were added to application settings.
- [ ] Two distinct private local buckets are initialized idempotently.
- [ ] Browser CORS permits direct GETs from both supported Vite origins.
- [ ] Existing CI suites run without LocalStack.
- [ ] Fresh imports write canonical keys to the LocalStack user-media bucket.
- [ ] `/media/access` returns 60-second direct grants.
- [ ] Browser retrieves bytes directly from LocalStack.
- [ ] Missing and foreign references remain indistinguishable.
- [ ] Partial success preserves successful grants.
- [ ] Expired URLs fail and fresh grants work.
- [ ] A missing object still receives a grant without a preflight `HeadObject`.
- [ ] Logs do not expose signed URLs or signatures.
- [ ] Live AWS-specific verification remains explicitly separate.
