# KrakenD Local Pass-Through Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local Dockerized KrakenD Community Edition gateway that transparently proxies the complete current FastAPI contract for the React/Vite application.

**Architecture:** KrakenD runs in Docker on loopback port `8081` and forwards each explicitly declared method/path to the host FastAPI process on port `8010`. Static `no-op` routes preserve request bodies, response bodies, statuses, headers, media, and repeated query parameters; backend authentication and authorization remain unchanged.

**Tech Stack:** KrakenD CE `2.13.8`, Docker Compose, FastAPI/OpenAPI, pytest, React/Vite, TypeScript, pnpm.

## Global Constraints

- Do not change `CurrentUserDep`, roles, authorization rules, route paths, response schemas, services, Redis/Dramatiq, database behavior, or FastAPI CORS.
- Do not add JWT/OIDC/Clerk, identity headers, rate limits, TLS, production deployment, FastAPI containerization, plugins, templates, transformations, or aggregation.
- Keep FastAPI directly available on `127.0.0.1:8010`; bind KrakenD only to `127.0.0.1:8081`.
- Build all gateway route coverage from the current FastAPI OpenAPI contract.

---

### Task 1: Static Gateway Contract

**Files:**
- Create: `backend/tests/infra/test_krakend_config.py`
- Create: `infra/krakend/Dockerfile`
- Create: `infra/krakend/krakend.json`

**Interfaces:**
- Consumes: `create_app().openapi()["paths"]`.
- Produces: a validated immutable image config containing all 38 application route/method pairs and four documentation routes.

- [x] Write a failing pytest that compares OpenAPI route/method pairs with KrakenD config and validates every pass-through invariant.
- [x] Run the focused test and verify it fails because the config is absent.
- [x] Add the pinned multi-stage Dockerfile and static 42-endpoint `no-op` config.
- [x] Run the focused test and Ruff checks.

### Task 2: Local Runtime Wiring

**Files:**
- Modify: `docker-compose.yml`
- Modify: `Makefile`
- Modify: `frontend/.env.example`
- Modify: `frontend/src/api/client.ts`

**Interfaces:**
- Consumes: KrakenD container port `8080` and host FastAPI port `8010`.
- Produces: local gateway port `8081`, gateway lifecycle commands, and a frontend default API/media base at `http://127.0.0.1:8081`.

- [x] Add focused frontend coverage for configured request and media URLs where needed.
- [x] Add the loopback-only Compose service with `host.docker.internal` mapping and no service dependencies.
- [x] Make backend port and gateway Make targets explicit.
- [x] Switch only the frontend API base example/fallback; preserve all endpoint paths and headers.
- [x] Run frontend tests and typecheck.

### Task 3: Local Operations Documentation

**Files:**
- Create: `infra/krakend/README.md`
- Create: `docs/manual-testing/krakend-pass-through.md`
- Modify: `README.md`

**Interfaces:**
- Produces: exact four-terminal startup instructions, gateway diagnostics, and the manual compatibility checklist.

- [x] Document topology, `no-op`, temporary query wildcard, validation, logs, and deferred production/auth work.
- [x] Update root startup order and resolve the old SQLite dashboard `8081` conflict by moving it to `8082`.
- [x] Add the complete reachability, roles, recipes, imports, media, search, CORS, and direct-comparison checklist.

### Task 4: Verification and Phase Close

**Files:**
- Verify: all files above and current phase/TODO/invariant documents.

**Interfaces:**
- Produces: evidence for static contract, tests, build, runtime health, and explicitly deferred manual checks.

- [x] Run full backend tests, Ruff lint, and format checks; distinguish pre-existing migration-wide issues if present.
- [x] Run frontend tests, typecheck, and production build.
- [x] Run `docker compose config` and build the validator/image.
- [x] When Docker is available, start KrakenD and verify `/__health`; verify proxied `/health` only with FastAPI actually running.
- [x] Search for stale frontend/direct API URLs and confirm only intentional upstream documentation remains.
- [x] Review refactoring needs against `docs/refactoring-guidelines.md`, check invariants and TODOs, and report any uncovered phase scope without starting the next phase.
