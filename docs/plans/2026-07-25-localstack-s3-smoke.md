# LocalStack S3 Smoke Testing Implementation Plan

> **Implementation/verification record:** PR #15 implemented the LocalStack service, configuration, integration tests, and runbook while adding this plan. Unchecked boxes preserve the original plan and are not proof of missing code. PR [#58](https://github.com/starkovalera/recipe-manager/pull/58) records the LocalStack + PREVIEW closure; live-AWS-only verification is extracted to [#59](https://github.com/starkovalera/recipe-manager/issues/59). Complete the shared [`Development Task Completion Checkpoint`](../agents/task-completion.md) if that closure task changes code.

## Acceptance closure — 2026-08-14

The LocalStack functional tier and the signed-in PREVIEW/browser tier are verified in draft PR [#58](https://github.com/starkovalera/recipe-manager/pull/58). The original implementation checklist below is retained for traceability; every checkbox now carries an explicit status. `Implemented in PR #15` means the code or documentation exists in the current repository and was not re-created by this closure task. `Verified` means the command or behavior was exercised during this acceptance run. The AWS-only boundary remains intentionally open in [#59](https://github.com/starkovalera/recipe-manager/issues/59).

### Deterministic evidence

- Environment: Windows PowerShell; Docker `29.5.3`; Docker Compose `v5.1.4`; LocalStack image `localstack/localstack:4.14.0`; CPython `3.13.5`; uv `0.11.24`; Node `v24.18.0`; pnpm `11.19.0`.
- `docker compose --profile local-s3 config`: passed; LocalStack is opt-in and exposes only `127.0.0.1:4566`.
- `docker compose --profile local-s3 up -d localstack` and `ps`: passed; container healthy. Initialization created both private buckets, and rerunning the init hook completed successfully without duplicate-bucket errors.
- Bucket checks: both buckets returned all four public-access-block settings as `true`; ACLs contained only the owner `FULL_CONTROL` grant; user-media CORS matched both Vite origins, `GET`, exposed headers, and `MaxAgeSeconds=300`.
- Backend setup and checks: `uv sync --frozen`; focused contract/infrastructure suite `94 passed`; full suite without `RUN_LOCALSTACK_INTEGRATION` `813 passed, 4 skipped, 24 warnings`; `ruff check` passed; `ruff format --check` reported `369 files already formatted`.
- Frontend and gateway checks: `14 passed` test files / `71 passed` tests; TypeScript typecheck and production build passed; `make gateway-check` passed with `50` KrakenD endpoints.
- Opt-in LocalStack module: with `AWS_ACCESS_KEY_ID=test`, `AWS_SECRET_ACCESS_KEY=test`, and `RUN_LOCALSTACK_INTEGRATION=1`, `4 passed in 10.65s`.
- The missing-object test received a direct grant and observed LocalStack `404`; the expiry test observed `200` before expiry and `403` after a shortened five-second TTL. Production `backend/app` contains no `HeadObject`/`head_object` match.
- The signed-in browser accepted the email-code flow, rendered a real LocalStack-backed PNG at `1440x1292`, returned HTTP `200` for an owned/foreign/missing batch with one grant and two `MEDIA_NOT_FOUND` items, refreshed the 60-second grant after its browser refresh window, and exercised a dangling database row without a grant-time object lookup.
- Targeted authorization/service tests passed `6 passed, 1 warning`; disposable database rows and LocalStack objects were removed afterward and the Preview recipe list was empty.
- No real credentials were used or committed. The only credential literals in tracked documentation/configuration are the fixed LocalStack test values `test`, supplied through the process environment or Compose.

### Intentionally unverified boundaries

- Live AWS IAM, Block Public Access enforcement, CloudTrail, AWS networking/TLS, exact AWS missing-object authorization, and production S3 verification remain open in [#59](https://github.com/starkovalera/recipe-manager/issues/59). The owner must provide a disposable private bucket, region, and an authorized short-lived/local AWS profile with the minimum required permissions; secret values must not be placed in the repository.
- The local PREVIEW request logger currently includes a local `databaseUrl` field. The media evidence contains no presigned URL, query signature, or storage key, but this is not a production log-hygiene approval.

### Development Task Completion Checkpoint

- This closure changes documentation only; no backend production or backend test files changed, so the backend refactoring review is not applicable.
- Documentation verification passed: `git diff --check` and relative Markdown-link resolution for the changed roadmap, architecture, plan, and runbook documents.
- No new speculative future-work item was discovered. The unverified browser/full-PREVIEW and live-AWS actions are existing owner boundaries recorded above and in the runbook.

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

- [x] **Step 1: Add failing settings tests** — **implemented in PR #15**; the current regression tests cover PREVIEW retention and PROD rejection.

Add tests that construct PREVIEW S3 settings with:

```python
aws_endpoint_url_s3="http://s3.localhost.localstack.cloud:4566"
```

and assert that the value is retained. Add a PROD test that passes the same value to `build_sqs_settings()` and expects a `ValidationError` mentioning `AWS_ENDPOINT_URL_S3` and `PROD`.

- [x] **Step 2: Isolate the test process from the endpoint environment variable** — **implemented in PR #15**.

Add `AWS_ENDPOINT_URL_S3` to the autouse environment cleanup fixture in `backend/tests/core/test_config.py` so a developer's LocalStack shell does not affect tests.

- [x] **Step 3: Run the focused test and confirm failure** — **historical-only**; the red phase is preserved by PR #15 history and was not repeated during this acceptance closure.

```powershell
cd backend
uv run pytest tests/core/test_config.py -q
```

Expected: the new tests fail because the field and PROD rule do not exist.

- [x] **Step 4: Add the setting and validation** — **implemented in PR #15**.

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

- [x] **Step 5: Run the focused settings tests** — **verified**; included in the focused backend run (`94 passed`).

```powershell
cd backend
uv run pytest tests/core/test_config.py -q
```

Expected: PASS.

- [x] **Step 6: Commit the configuration boundary** — **implemented in PR #15**; this closure task records evidence and does not recreate the historical implementation commit.

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

- [x] **Step 1: Add failing lazy-client tests** — **implemented in PR #15**; lazy construction, reuse, and endpoint assertions are present.

Extend the existing boto3 factory assertions so configured adapters call:

```python
boto3.client(
    "s3",
    region_name="us-east-1",
    endpoint_url="http://s3.localhost.localstack.cloud:4566",
)
```

Retain coverage that client construction is lazy and the client is reused.

- [x] **Step 2: Add failing runtime propagation tests** — **implemented in PR #15**.

Build PREVIEW S3 settings with the LocalStack endpoint, patch the adapter constructors, invoke `get_storage_service(settings)` and `get_download_access_provider(settings)`, and assert both receive the same endpoint.

- [x] **Step 3: Run the focused adapter tests and confirm failure** — **historical-only**; the red phase was not repeated during this closure.

```powershell
cd backend
uv run pytest tests/storage/test_runtime.py tests/storage/test_s3.py tests/media/test_access_providers.py -q
```

Expected: the new endpoint assertions fail.

- [x] **Step 4: Implement endpoint propagation** — **implemented in PR #15** and exercised by the focused tests.

Add `endpoint_url: str | None = None` to both S3 adapter constructors, store it, and pass it when lazily constructing each boto3 client. Runtime factories pass `resolved_settings.aws_endpoint_url_s3` to their adapter.

Do not add a new one-call S3 client factory. The existing storage and download adapters retain responsibility for their own lazy clients.

- [x] **Step 5: Run the focused adapter tests** — **verified**; included in the focused backend run (`94 passed`).

```powershell
cd backend
uv run pytest tests/storage/test_runtime.py tests/storage/test_s3.py tests/media/test_access_providers.py -q
```

Expected: PASS.

- [x] **Step 6: Run the infrastructure boundary test** — **verified**; included in the focused backend run (`94 passed`).

```powershell
cd backend
uv run pytest tests/infra/test_queue_publishing_boundary.py tests/infra/test_storage_transaction_boundaries.py -q
```

Expected: PASS; no boto3 use leaks into application/domain modules.

- [x] **Step 7: Commit adapter support** — **implemented in PR #15**; this closure task does not recreate the historical implementation commit.

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

- [x] **Step 1: Add the LocalStack service** — **implemented in PR #15** and verified through Compose rendering and a healthy pinned container.

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

- [x] **Step 2: Create the idempotent initialization script** — **implemented and verified**; the mounted hook was rerun successfully, and bucket privacy/CORS were inspected.

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

- [x] **Step 3: Validate Compose rendering** — **verified**; `docker compose --profile local-s3 config` exited `0`.

```powershell
docker compose --profile local-s3 config
```

Expected: exit code `0`; no missing environment interpolation and only loopback port exposure for LocalStack.

- [x] **Step 4: Start LocalStack and verify initialization** — **verified**; the service was healthy and both expected buckets were listed.

```powershell
docker compose --profile local-s3 up -d localstack
docker compose --profile local-s3 ps localstack
docker compose --profile local-s3 exec localstack awslocal s3api list-buckets
```

Expected: healthy service and both local bucket names in the response.

- [x] **Step 5: Verify the buckets remain private** — **verified**; public-access-block was enabled on both buckets and ACLs contained only the owner grant.

```powershell
docker compose --profile local-s3 exec localstack awslocal s3api get-public-access-block --bucket recipe-manager-local-user-media
```

If LocalStack does not synthesize a public-access-block response for a newly created bucket, verify instead that there is no bucket policy or public ACL. Record the emulator limitation in the runbook; do not add a public policy to make the check pass.

- [x] **Step 6: Commit LocalStack infrastructure** — **implemented in PR #15**; this closure task does not recreate the historical implementation commit.

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

- [x] **Step 1: Document non-secret backend overrides** — **implemented in PR #15**; only fixed LocalStack test values are documented, never application credential fields.

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

- [x] **Step 2: Document the Windows startup sequence** — **implemented in PR #15** and retained in the README and owner runbook.

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

- [x] **Step 3: Document reset and inspection commands** — **implemented and verified** against the opt-in Compose service; PREVIEW database and LocalStack reset remain separate.

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

- [x] **Step 4: Add a LocalStack section to the P10 runbook** — **implemented in PR #15**; this closure adds dated evidence and preserves the live-AWS boundary.

Keep the existing LOCAL/PREVIEW and Live S3 sections. Insert LocalStack as an intermediate test tier and clearly state which production claims it cannot validate: real IAM permissions, AWS Block Public Access enforcement, CloudTrail evidence, AWS networking/TLS, and exact real-S3 missing-object authorization behavior.

- [x] **Step 5: Validate documentation commands against Compose** — **verified** for config, startup/status, bucket listing, ACL/public-access-block, CORS, and idempotent init-hook commands.

Run each non-destructive command from the repository root and correct any Windows/Compose mismatch.

- [x] **Step 6: Commit documentation** — **implemented in PR #15**; this closure updates the plan and runbook with acceptance evidence.

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

- [x] **Step 1: Run backend checks without LocalStack** — **verified**; full pytest `813 passed, 4 skipped`, Ruff check/format passed, and the opt-in module remained skipped without its flag.

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

- [x] **Step 2: Run frontend and gateway checks** — **verified**; frontend `71 passed`, typecheck/build passed, and KrakenD validation reported `50` endpoints.

```powershell
cd frontend
pnpm exec vitest run
pnpm run typecheck
pnpm run build
```

Then run the repository's existing KrakenD validation command documented by the current gateway test setup.

- [x] **Step 3: Start the complete PREVIEW + LocalStack stack** — **verified**; the full PostgreSQL/Redis/Adminer/KrakenD/FastAPI/Dramatiq/Vite stack, Clerk email-code sign-in, and LocalStack health were exercised in the browser run.

Start PostgreSQL, Redis, Adminer, KrakenD, LocalStack, FastAPI, Dramatiq, and Vite using the documented commands. Confirm KrakenD `/__health`, backend `/health`, LocalStack health, and frontend sign-in before testing imports.

- [x] **Step 4: Create fresh S3-backed data** — **verified**; the signed-in PREVIEW import evidence in the runbook recorded fresh S3-backed rows/objects and disposable cleanup.

Import a new image or supported URL after S3 mode is active. Do not use recipes created under LOCAL storage, because their database keys may exist while the corresponding LocalStack objects do not.

Verify the canonical object key appears under the user-media bucket:

```powershell
docker compose --profile local-s3 exec localstack awslocal s3 ls s3://recipe-manager-local-user-media --recursive
```

- [x] **Step 5: Verify the grant contract** — **verified**; browser Network observed HTTP `200`, `accessMode=direct`, approximately 60-second expiry, stable IDs in the request shape, and no `mediaUrl` or storage-key fields.

In browser Network, inspect successful `POST /media/access`:

- HTTP `200`;
- `accessMode` is `direct`;
- `expiresAt` is approximately 60 seconds after response time;
- grant URL targets LocalStack on port `4566`;
- response contains no bucket name or storage key outside the signed URL;
- the recipe/media domain responses expose stable IDs rather than storage keys.

- [x] **Step 6: Verify direct browser retrieval** — **verified**; the image GET went directly to the LocalStack S3 host, returned `image/png` with HTTP `200`, and decoded in the browser at `1440x1292`.

Open the presigned request in Network and confirm its remote address is LocalStack `:4566`, not KrakenD `:8081` or FastAPI `:8010`. Confirm the expected MIME type and bytes are returned.

- [x] **Step 7: Verify partial success and normalized authorization failures** — **verified**; the authenticated batch returned one owned grant and indistinguishable `MEDIA_NOT_FOUND` items for foreign and missing IDs.

Request one owned stable media ID plus `missing-p10-media-id`. Confirm HTTP `200`, one grant, and one `MEDIA_NOT_FOUND`. Repeat with a known foreign ID and confirm its item is indistinguishable from the missing-ID item.

- [x] **Step 8: Verify expiry** — **verified**; the five-second LocalStack test rejected the old URL, and the browser refreshed its normal 60-second grant after the refresh window with a new HTTP `200` access response.

Save one signed URL, wait more than 60 seconds, and request it again. Confirm the old URL is rejected. Request a fresh grant through `/media/access` and confirm the new URL retrieves the bytes.

- [x] **Step 9: Verify a dangling DB reference** — **verified**; the owned database row retained a direct grant without `HeadObject`, while the deleted LocalStack object failed only at retrieval.

Delete an object's bytes through `awslocal` while leaving its owned database row intact. Request `/media/access` and confirm it still returns a direct signed grant without `HeadObject`; requesting that URL from LocalStack returns the emulator's missing-object response.

- [x] **Step 10: Inspect logs** — **verified for the media boundary**; sanitized media evidence contained no signed URL, query signature, or storage key, LocalStack direct GETs were observed, and static production search found no `HeadObject`. Existing PREVIEW logs still include a local `databaseUrl`, so production log hygiene remains outside this closure.

Search backend, worker, KrakenD, and LocalStack logs. Confirm backend/application logs contain no full presigned URL, signature, bucket name, or storage key. Confirm LocalStack records direct GETs and no application-triggered `HeadObject` for grant creation.

- [x] **Step 11: Reset disposable state** — **verified**; the LocalStack container was recreated for this run and the init hook was rerun successfully. A documented reset command remains available for owners.

Recreate the LocalStack container and restart PREVIEW when a clean database is required. Confirm the two bucket initialization hook runs successfully after recreation.

- [x] **Step 12: Record evidence and remaining live-AWS gap** — **verified** in this dated closure section and the owner runbook; live AWS remains a separate owner prerequisite.

Record exact check totals and manual outcomes. Mark LocalStack functional verification complete, but leave live AWS IAM/Block Public Access/CloudTrail verification open until tested against a private AWS bucket.

---

## Acceptance Checklist

- [x] LocalStack is opt-in and normal PREVIEW remains `LOCAL` storage by default — **verified** by Compose profile/configuration and the backend settings/tests.
- [x] Both application S3 clients use the same custom endpoint — **verified** by the focused runtime/adapter tests and the direct LocalStack integration.
- [x] PROD rejects `AWS_ENDPOINT_URL_S3` — **verified** by the focused configuration tests.
- [x] No AWS credential fields were added to application settings — **verified** by the settings contract and tracked-file review.
- [x] Two distinct private local buckets are initialized idempotently — **verified** by bucket listing, public-access-block/ACL checks, and a successful init-hook rerun.
- [x] Browser CORS permits direct GETs from both supported Vite origins — **verified** by the LocalStack CORS response and the signed-in browser image GET.
- [x] Existing CI suites run without LocalStack — **verified** by the full backend suite, frontend suite/build, and gateway validation run before the LocalStack integration.
- [x] Fresh imports write canonical keys to the LocalStack user-media bucket — **verified** by the signed-in PREVIEW import evidence in the runbook; disposable rows/objects were removed after the check.
- [x] `/media/access` returns 60-second direct grants — **verified** at the provider seam (`55–65s` metadata window) and in browser Network with a refresh response.
- [x] Browser retrieves bytes directly from LocalStack — **verified** by a signed-in browser GET returning `image/png` and decoding at `1440x1292`.
- [x] Missing and foreign references remain indistinguishable — **verified** by the authenticated batch response.
- [x] Partial success preserves successful grants — **verified** by the same authenticated batch response.
- [x] Expired URLs fail and fresh grants work — **verified** by the opt-in five-second expiry test plus the browser's normal 60-second refresh window.
- [x] A missing object still receives a grant without a preflight `HeadObject` — **verified** by the missing-object integration and no production `HeadObject`/`head_object` match.
- [x] Logs do not expose signed URLs or signatures in the media evidence — **verified**; the existing local Preview `databaseUrl` field is explicitly not approved for production logging.
- [x] Live AWS-specific verification remains explicitly separate — **verified** by the runbook and the owner-prerequisite statement above.
