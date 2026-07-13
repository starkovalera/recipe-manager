# KrakenD Local Gateway

KrakenD Community Edition `2.13.8` is the local pass-through gateway for the Recipe Manager frontend.

```text
React/Vite :5173
    -> KrakenD container 127.0.0.1:8081
    -> FastAPI host process host.docker.internal:8010
    -> PostgreSQL :5432 / Redis :6379
```

FastAPI intentionally remains outside Docker and directly reachable on `127.0.0.1:8010` during this compatibility phase. The gateway has no Compose dependency on FastAPI, PostgreSQL, or Redis.

## Pass-Through Contract

Every current FastAPI method/path pair is declared explicitly in `krakend.json`. Both endpoint and backend use `no-op` encoding so KrakenD preserves multipart and JSON request bodies, binary media, backend status codes, response headers, JSON error bodies, and empty `204` responses.

`input_query_strings: ["*"]` temporarily forwards all existing query parameters, including repeated values. This is a local compatibility policy, not the intended production allowlist.

FastAPI CORS remains enabled. KrakenD also handles local browser CORS for Vite origins on ports `5173`.

The CORS header allowlist also contains `*` as a local KrakenD `2.13.8` compatibility workaround. Without it, the pinned runtime accepts each configured custom header separately but rejects a browser preflight that requests multiple allowed headers together. Origins remain restricted to the two local Vite URLs, and the gateway remains bound to loopback. Reassess this workaround before using the configuration outside local development.

## Validation and Runtime

Validate the static config in the pinned image:

```powershell
docker build --target validator -t recipe-manager-krakend-check ./infra/krakend
```

Build and start the gateway:

```powershell
docker compose up -d --build krakend
curl.exe http://127.0.0.1:8081/__health
```

Inspect logs or stop the gateway:

```powershell
docker compose logs -f krakend
docker compose stop krakend
```

`/__health` checks KrakenD itself. `/health` is an explicitly configured pass-through route and requires FastAPI to be running on port `8010`.

Clerk/JWT validation, trusted identity headers, rate limits, TLS, production networking, FastAPI containerization, plugins, templates, and response transformations are deferred.
