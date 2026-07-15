# KrakenD Local Authenticated Gateway

KrakenD Community Edition `2.13.8` is the local browser ingress and Clerk JWT validation boundary.

```text
React/Vite :5173
    -> KrakenD container 127.0.0.1:8081
    -> FastAPI host process host.docker.internal:8010
    -> PostgreSQL :5432 / Redis :6379
```

FastAPI remains directly reachable on `127.0.0.1:8010` for upstream diagnostics. It must not be exposed as a production ingress because direct access bypasses JWT validation.

## Authentication Boundary

Protected browser requests carry a Clerk Bearer token to KrakenD. The Flexible Configuration template:

- validates RS256 signature, `CLERK_ISSUER`, and `CLERK_JWKS_URL`;
- caches JWKS data;
- propagates the verified `sub` claim as `X-Authenticated-Subject`;
- does not forward the browser `Authorization` header;
- does not allow the browser to provide the trusted subject header through CORS.

FastAPI trusts the propagated subject as an authenticated identity, then performs internal-user status, role, owner, and domain checks. Gateway authentication never replaces backend authorization.

Public routes are limited to health, Clerk webhooks, and FastAPI documentation routes. `POST /webhooks/clerk` is public because provider webhooks have no end-user session; FastAPI verifies its raw body with Svix signature headers.

## Route Contract

Every FastAPI method/path pair is declared in `config/endpoints.json`. The template uses `no-op` encoding to preserve multipart and JSON bodies, binary media, backend status codes, response headers, JSON errors, and empty `204` responses.

`input_query_strings: ["*"]` temporarily forwards all query parameters, including repeated values. This is a local compatibility policy, not the intended production allowlist.

`backend/tests/infra/test_krakend_config.py` enforces:

- exact OpenAPI/gateway route parity;
- unique route entries;
- the complete public-route allowlist;
- JWT validation and trusted-subject propagation;
- no upstream Authorization forwarding;
- required Svix headers on the webhook route.

## Local Configuration

Create an ignored root `.env`:

```dotenv
CLERK_ISSUER=https://<instance>.clerk.accounts.dev
CLERK_JWKS_URL=https://<instance>.clerk.accounts.dev/.well-known/jwks.json
```

The Compose file permits config-only diagnostics without values, but `entrypoint.sh` refuses to start KrakenD until both variables are non-empty.

## CORS

KrakenD permits local Vite origins on ports `5173`, Bearer authentication, multipart uploads, mutation methods, and the existing client/idempotency headers. FastAPI CORS remains enabled for direct diagnostics.

The local configuration is bound to loopback. Before production, verify the narrowest working headers/origins against the selected KrakenD version and replace the wildcard query forwarding with explicit endpoint allowlists.

## Validation and Runtime

Validate the Flexible Configuration render in the pinned image:

```powershell
docker build --target validator -t recipe-manager-krakend-check ./infra/krakend
docker compose build krakend
```

Build and start:

```powershell
docker compose up -d --build krakend
curl.exe http://127.0.0.1:8081/__health
curl.exe http://127.0.0.1:8081/health
```

Inspect or stop:

```powershell
docker compose logs -f krakend
docker compose stop krakend
```

`/__health` checks KrakenD itself. `/health` is public but proxied to FastAPI and fails when the upstream is unavailable.

For a complete browser and API checklist, use `docs/manual-testing/krakend-pass-through.md` and `docs/manual-testing/clerk-lifecycle.md`.
