# P10 Owner Verification Runbook

Use the branch SHA recorded in the draft PR. Automated tests cover authorization,
contracts, LOCAL bytes, S3 signing, frontend retrieval modes, and gateway parity.
The checks below require the repository owner because they use a browser session
or AWS credentials.

## LocalStack acceptance evidence — 2026-08-14

The agent-run functional tier completed on branch `codex/issue-26-localstack-acceptance`.
This evidence does not claim the owner-only browser, Clerk, full PREVIEW-stack, or
live-AWS checks below.

- Docker `29.5.3` / Compose `v5.1.4`; pinned image `localstack/localstack:4.14.0`.
- `docker compose --profile local-s3 config` passed; the service is opt-in and
  binds only `127.0.0.1:4566`.
- LocalStack became healthy and initialized both
  `recipe-manager-local-user-media` and
  `recipe-manager-local-system-artifacts`. Re-running the init hook was
  idempotent.
- Both buckets returned `BlockPublicAcls`, `IgnorePublicAcls`,
  `BlockPublicPolicy`, and `RestrictPublicBuckets` as `true`; ACLs contained only
  the owner `FULL_CONTROL` grant. User-media CORS allowed both supported Vite
  origins and `GET` with the documented exposed headers.
- Backend baseline: `813 passed, 4 skipped, 24 warnings`; focused contract and
  infrastructure checks: `94 passed`; Ruff check and format check passed.
- Frontend baseline: `14` test files and `71` tests passed; typecheck and build
  passed. KrakenD validation passed with `50` endpoints.
- Opt-in S3 integration: `4 passed in 10.65s`, covering storage round-trip/list,
  direct presigned retrieval, missing-object grant without a preflight lookup,
  and shortened-TTL expiry rejection.
- A static search found no `HeadObject`/`head_object` reference in production
  `backend/app`. No real credentials or signed URLs were recorded.

The following LocalStack owner steps remain open: complete PREVIEW stack startup,
Clerk sign-in, fresh import, browser Network/direct-CORS checks, the authenticated
partial-success/foreign-reference flow, and backend/worker/KrakenD log inspection.
The Live S3 section remains a separate owner prerequisite and must use a disposable
private bucket plus an authorized short-lived/local AWS profile; record evidence,
never secret values.

## LOCAL / PREVIEW

Prerequisites: PostgreSQL, Redis, KrakenD, backend, worker, and frontend started
with the normal PREVIEW configuration and a signed-in Clerk test user.

### Clerk development sign-in

For the seeded `+clerk_test` users, use the email-code path rather than a password:

1. Enter the email from `backend/config/preview-users.local.toml` and select
   **Continue**.
2. Select **Email code to …**.
3. Enter the fixed Clerk development code `424242`.
4. Wait for the application home page and `POST /me/provision` to complete.

Clerk may reject the seed password as compromised. The fixed code is only for
Clerk development test users and must not be used for non-test accounts.

1. Import one image and one supported URL containing images.
2. Confirm the recipe grid, recipe hero, cover choices, preview modal, and import
   detail images render through KrakenD.
3. In browser Network, confirm domain responses contain image/source IDs and no
   `mediaUrl` or storage keys.
4. Confirm one or more `POST /media/access` requests return
   `accessMode=authenticated_fetch` and stable `/media/{type}/{id}` URLs.
5. Confirm each LOCAL GET includes `Authorization` and returns the expected MIME
   type and bytes.
6. Delete or hide the owning recipe and confirm a fresh access request returns
   `MEDIA_NOT_FOUND` for its image.
7. Confirm default recipe SVGs render without a media-access request.

## LocalStack S3 / PREVIEW

This tier exercises the real boto3 S3 adapters, storage keys, presigned URLs,
browser CORS, signature expiry, and direct browser downloads without an AWS
account. It does not replace the Live S3 checks for IAM and AWS infrastructure.

1. Add the documented LocalStack S3 overrides to ignored `backend/.env`.
2. Start LocalStack from the repository root:

   ```powershell
   docker compose --profile local-s3 up -d localstack
   docker compose --profile local-s3 ps localstack
   ```

3. Set `AWS_ACCESS_KEY_ID=test` and `AWS_SECRET_ACCESS_KEY=test` in both the
   FastAPI and Dramatiq terminals, then restart both processes.
4. Run the opt-in integration suite:

   ```powershell
   cd backend
   New-Item -ItemType Directory -Force .pytest-tmp | Out-Null
   $env:AWS_ACCESS_KEY_ID="test"
   $env:AWS_SECRET_ACCESS_KEY="test"
   $env:RUN_LOCALSTACK_INTEGRATION="1"
   uv run pytest tests/integration/localstack/test_s3_media_flow.py -q --basetemp=.pytest-tmp/localstack-integration
   ```

5. Import at least two images together so the import pipeline creates fresh
   S3-backed rows and objects. Do not use pre-existing LOCAL-backed recipes as
   evidence for this check.
6. Confirm canonical objects exist:

   ```powershell
   docker compose --profile local-s3 exec localstack awslocal s3 ls s3://recipe-manager-local-user-media --recursive
   ```

7. In browser Network, confirm `POST /media/access` returns `accessMode=direct`,
   `expiresAt` approximately 60 seconds after the response, and a grant URL on
   LocalStack port `4566`.
8. Confirm the image GET goes directly to LocalStack, not KrakenD `8081` or
   FastAPI `8010`, and returns the expected MIME type and bytes.
9. Request one owned item together with a missing ID. Confirm HTTP `200`, one
   successful grant, and one `MEDIA_NOT_FOUND`. Confirm a foreign ID has the same
   item-level response as the missing ID.
10. Reuse a signed URL after its expiry and confirm it fails. Request a fresh
    grant and confirm the new URL succeeds.
11. Delete an object's bytes through `awslocal` while retaining its database row.
    Confirm `/media/access` still returns a signed URL without `HeadObject`, then
    confirm LocalStack GET returns its missing-object response.
12. Inspect backend, worker, KrakenD, and LocalStack logs. Application logs must
    not contain signed URLs or query signatures. LocalStack should show direct
    browser GETs and no grant-time `HeadObject`.
13. Reset the disposable S3 environment independently when needed:

    ```powershell
    docker compose --profile local-s3 rm -sf localstack
    docker compose --profile local-s3 up -d localstack
    ```

LocalStack does not validate real IAM policy scope, AWS Block Public Access
enforcement, CloudTrail evidence, production DNS/TLS, or every AWS-specific
missing-object authorization response. Those remain in the Live S3 tier.

## Live S3

Prerequisites: a private disposable user-media bucket, an AWS region, and
credentials with narrowly scoped `s3:GetObject` access. Do not commit values.

1. Configure PROD-compatible S3 settings and put one test image under a canonical
   `USER_MEDIA` key represented by a test database row.
2. Request `POST /media/access` for the owned stable ID.
3. Confirm `accessMode=direct`, `expiresAt` is approximately 60 seconds after the
   response, and the URL retrieves the object directly from S3.
4. Confirm backend logs contain no presigned URL or query signature.
5. Confirm a foreign user receives the same `MEDIA_NOT_FOUND` item as a missing ID.
6. Confirm the FastAPI GET media route does not proxy S3 content.

Live S3 verification remains a gap until the owner supplies the private bucket
and credentials and records the result in the PR.
