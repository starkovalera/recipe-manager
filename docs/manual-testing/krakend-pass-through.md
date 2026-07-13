# KrakenD Pass-Through Manual Testing

Use this checklist after the automated gateway checks pass.

## Prerequisites

- [ ] PostgreSQL is running.
- [ ] Redis is running.
- [ ] KrakenD is running on `127.0.0.1:8081`.
- [ ] FastAPI is running on `127.0.0.1:8010`.
- [ ] Dramatiq worker is running.
- [ ] Frontend is running on `127.0.0.1:5173`.
- [ ] `frontend/.env` contains `VITE_API_BASE_URL=http://127.0.0.1:8081`.

## Reachability

- [ ] `GET http://127.0.0.1:8081/__health` returns `200` from KrakenD.
- [ ] `GET http://127.0.0.1:8081/health` returns FastAPI `{"status":"ok"}`.
- [ ] Stop FastAPI and confirm `/__health` still works while proxied `/health` fails.
- [ ] Restart FastAPI and confirm proxying resumes without rebuilding KrakenD.

## User and Admin

- [ ] `/me` loads through KrakenD.
- [ ] Admin visibility matches the capabilities returned for the current user.
- [ ] Role management loads and a non-final role can be assigned and revoked.
- [ ] Do not revoke the final `superadmin` role during this test.

## Recipes

- [ ] Recipe list and detail load.
- [ ] Recipe update and delete still work.
- [ ] Recipe debug sections still follow backend roles.
- [ ] Repeated query parameters, including multiple `ingredientQuery` values, survive gateway forwarding.
- [ ] Backend error status codes and JSON response bodies are preserved.

## Imports

- [ ] Multipart image upload works.
- [ ] URL and text imports work.
- [ ] `X-Client-Id` reaches FastAPI.
- [ ] `Idempotency-Key` behavior remains intact.
- [ ] Import polling and notifications work.
- [ ] Normal user import retry works.
- [ ] Internal admin import retry works.
- [ ] The Dramatiq worker completes the import job.

## Media

- [ ] Images load from `http://127.0.0.1:8081/media/...`.
- [ ] Missing media preserves the backend `404` response.
- [ ] Media response `Content-Type` is correct.

## Search and Internal Pages

- [ ] Ordinary search and selected chips work.
- [ ] Search Debug works.
- [ ] Import Jobs, Embeddings, and Roles load through the single Admin entry.
- [ ] Embedding retry works.
- [ ] The frontend still has one top-level Admin entry.

## CORS

- [ ] The browser console has no CORS errors.
- [ ] Multipart preflight succeeds.
- [ ] `PATCH`, `PUT`, `DELETE`, `X-Client-Id`, and `Idempotency-Key` pass preflight.

## Direct Comparison

Compare representative requests through both URLs:

```text
http://127.0.0.1:8010/<path>
http://127.0.0.1:8081/<path>
```

- [ ] Status codes are equivalent.
- [ ] Response bodies are equivalent.
- [ ] Important response headers are equivalent.

For every failure, capture:

```text
path and method
gateway response
direct FastAPI response
KrakenD logs
FastAPI logs
browser console error
```
