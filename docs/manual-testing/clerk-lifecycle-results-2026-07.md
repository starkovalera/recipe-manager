# Clerk Lifecycle Manual Test Results — July 2026

## Scope

Manual testing was performed against the local PREVIEW topology:

- React/Vite frontend;
- KrakenD local gateway;
- FastAPI;
- PostgreSQL;
- Redis and Dramatiq where deletion processing required them;
- Clerk development instance in Restricted mode;
- Clerk CLI webhook relay forwarding through KrakenD.

Tested source branch: `codex/source-tree-ai-sources`

Tested commit: `b8e1337e90988add57ae4a0fb244f540ede89509`

## Result

All scenarios listed below completed successfully.

## Verified scenarios

- Signed Clerk webhook delivery through relay, KrakenD, FastAPI, Svix verification, and PostgreSQL.
- Duplicate webhook delivery returned HTTP 200 and did not duplicate or mutate user data.
- Real `user.created`, `user.updated`, and `user.deleted` lifecycle handling.
- Invitation creation by a superadmin.
- Invitation acceptance and local `PENDING -> ACCEPTED` synchronization.
- Invitation revocation and rejection of the revoked invitation link.
- Role and capability matrix for `DEBUG`, `SUPERADMIN`, and ordinary users.
- Backend rejection of invitation, role, and status administration by non-superadmins.
- Role assignment and revocation.
- Protection against removing the final `SUPERADMIN`.
- User deactivation and reactivation.
- Protection against deactivating or deleting the last active superadmin.
- Self-service account deletion.
- Durable `DELETION_PENDING` state before worker execution.
- Account-deletion processing through Dramatiq.
- Deletion recovery after Redis/publishing outage through reconciliation.
- Missing JWT rejection at KrakenD.
- Invalid JWT rejection at KrakenD.
- Rejection of identity-header spoofing without a valid JWT.
- Verified JWT subject winning over a client-supplied `X-Authenticated-Subject`.

## Data checks

The tests verified the relevant sanitized PostgreSQL state, including:

- users;
- user settings;
- role assignments;
- invitations;
- Clerk webhook idempotency events;
- deletion-pending and final deletion states.

## Security note

This record intentionally contains no:

- JWTs;
- Clerk API keys;
- webhook signing secrets;
- Svix signatures;
- invitation tickets;
- raw webhook payloads;
- passwords;
- personal email aliases used for disposable testing.

## Limitations

These results validate the local PREVIEW implementation. They do not validate:

- Clerk production configuration;
- public production DNS or TLS;
- production KrakenD networking;
- SQS/Lambda delivery;
- S3 media storage;
- Terraform;
- CI/CD deployment;
- production monitoring or rollback.
