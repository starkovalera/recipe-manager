# Clerk Lifecycle Manual Testing

Use this checklist after automated backend, frontend, migration, and gateway checks pass. These tests require a real Clerk development instance and cannot be claimed from mocks alone.

## Clerk Instance Setup

- [ ] Clerk development instance uses Restricted mode so uninvited sign-up is rejected.
- [ ] Allowed frontend origins include `http://127.0.0.1:5173` and, if used, `http://localhost:5173`.
- [ ] The invitation redirect is `http://127.0.0.1:5173/sign-up`.
- [ ] A webhook endpoint subscribes to `user.created`, `user.updated`, and `user.deleted`.
- [ ] The webhook endpoint targets a public tunnel ending at `POST /webhooks/clerk` through KrakenD or FastAPI.
- [ ] The webhook signing secret matches `CLERK_WEBHOOK_SIGNING_SECRET`.

The Clerk CLI can link the project and pull keys:

```powershell
clerk auth login
clerk link
clerk env pull
```

Review pulled values before moving them into the repository's ignored root, backend, and frontend `.env` files. Do not commit secrets.

## Required Local Configuration

Root `.env`:

```dotenv
CLERK_ISSUER=https://<instance>.clerk.accounts.dev
CLERK_JWKS_URL=https://<instance>.clerk.accounts.dev/.well-known/jwks.json
```

`backend/.env`:

```dotenv
APP_ENV=PREVIEW
CLERK_SECRET_KEY=sk_test_...
CLERK_API_URL=https://api.clerk.com
CLERK_WEBHOOK_SIGNING_SECRET=whsec_...
FRONTEND_INVITATION_URL=http://127.0.0.1:5173/sign-up
PREVIEW_USERS_FILE=./config/preview-users.local.toml
```

`frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8081
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
```

## Startup

```powershell
# Terminal 1, repository root
docker compose up -d --build postgres redis adminer krakend

# Terminal 2, backend
uv run fastapi dev app/main.py --host 127.0.0.1 --port 8010

# Terminal 3, backend
uv run dramatiq app.worker

# Terminal 4, frontend
npm run dev
```

Optional preview bootstrap after migrations:

```powershell
uv run python -m app.local.seed_preview_users
```

For local webhook delivery, expose the selected webhook ingress with a tunnel, configure the exact public URL in Clerk, and verify the Clerk dashboard records a successful delivery. Clerk cannot deliver directly to localhost.

## Ordinary Login

- [ ] Signed-out users see only the authentication shell.
- [ ] A valid sign-in establishes a Clerk session.
- [ ] The first protected application request is `POST /me/provision` through KrakenD.
- [ ] Existing users receive `200`; first-time users receive `201`.
- [ ] Product queries do not start before provisioning succeeds.
- [ ] `/me` returns capabilities without exposing roles.
- [ ] Refreshing the page does not create duplicate users, settings, or tags.
- [ ] Signing out clears product data and protected navigation before another identity signs in.

## Invite-Only First Login

- [ ] An uninvited address cannot complete sign-up in Restricted mode.
- [ ] A superadmin can create an invitation from Admin > Invitations.
- [ ] The UI never displays a Clerk invitation ticket or provider URL.
- [ ] The invitation email opens `/sign-up` and the Clerk sign-up component accepts the ticket.
- [ ] Completing sign-up establishes a session and provisions exactly one internal user.
- [ ] The new user has settings/default tags but no privileged local role.
- [ ] The `user.created` webhook changes the matching local invitation to `ACCEPTED`.
- [ ] Replaying the same webhook does not duplicate data and reports `processed: false`.
- [ ] Revoking a pending invitation is idempotent.

## Role and Status Administration

- [ ] A non-superadmin cannot call invitation, role, or status administration endpoints.
- [ ] A superadmin can assign/revoke `DEBUG` and non-final `SUPERADMIN` roles.
- [ ] The last superadmin role cannot be revoked.
- [ ] The last active superadmin cannot be deactivated or deleted.
- [ ] A deactivated user sees the dedicated deactivated screen and no product content.
- [ ] Reactivating the user restores normal provisioning and product access on a new request/session bootstrap.

## Email Change

- [ ] Change and verify the primary email through Clerk account management.
- [ ] Clerk sends `user.updated` to the configured webhook.
- [ ] The normalized internal email changes after successful processing.
- [ ] Existing recipes and ownership remain linked to the same internal user ID.
- [ ] A collision with another internal user's email is rejected without auto-linking identities.
- [ ] Review Clerk/Svix retry attempts for the rejected collision event.

## Password Change

- [ ] Change the password through Clerk account management.
- [ ] Recipe Manager never requests or stores the password.
- [ ] The next API request uses a token from the current Clerk session.
- [ ] If the Clerk instance invalidates the session, the frontend returns to the signed-out shell and clears cached product data.

## Account Deletion

- [ ] Delete Account requires explicit confirmation.
- [ ] `POST /me/deletion` returns `202` with `DELETION_PENDING`.
- [ ] The frontend immediately clears token/query state, requests Clerk sign-out, and shows the neutral deletion screen.
- [ ] The user row is durably pending before the deletion task is published.
- [ ] A pending user cannot access product routes.
- [ ] The worker waits/retries while active imports exist.
- [ ] The worker removes the Clerk user, recipe/import media, and then the internal user with owned rows.
- [ ] Simulated storage failure leaves the user and owned rows in `DELETION_PENDING` for retry.
- [ ] Re-running deletion after partial provider cleanup is idempotent.
- [ ] `uv run python -m app.users.reconcile_deletions` republishes pending users after a worker/publish outage.
- [ ] A provider-side `user.deleted` event starts the same pending deletion lifecycle.

## Webhook Security and Recovery

- [ ] Missing or invalid Svix signatures are rejected.
- [ ] The webhook route is public at KrakenD but protected by signature verification in FastAPI.
- [ ] `ClerkWebhookEvent.event_id` equals the signed `svix-id` delivery header, not a field from the JSON body.
- [ ] Protected routes reject missing/invalid Clerk JWTs at KrakenD.
- [ ] Browser-supplied `X-Authenticated-Subject` is not accepted as an identity override.
- [ ] Failed webhook deliveries are visible in Clerk/Svix and can be replayed.
- [ ] Logs contain no JWT, Clerk secret, webhook signing secret, signature, invitation ticket, or raw webhook body.

### Dashboard Sample Versus Real User Event

The Clerk Dashboard synthetic `user.created` sample may contain an empty `email_addresses` array even when
`primary_email_address_id` is present. Recipe Manager rejects that payload with `400 INVALID_WEBHOOK` because the internal
`User` model requires a real primary email. This is payload validation after successful signature verification and does not
indicate that KrakenD failed to forward the raw body or Svix headers.

To verify complete `user.created` processing:

1. Keep the three predefined preview users unchanged.
2. Create a temporary user in the Clerk development instance with a unique, verified primary email.
3. Confirm that Clerk sends the resulting real `user.created` event to the configured public tunnel URL ending at
   `/webhooks/clerk`.
4. In the Clerk/Svix delivery view, confirm the relay result is `200 POST /webhooks/clerk`.
5. Confirm FastAPI returns `200` with `{"processed": true}`.
6. In PostgreSQL, confirm the internal user exists with `status = ACTIVE`, has no roles, and its auth identity matches the
   temporary Clerk user.
7. Confirm the corresponding `clerk_webhook_events.event_id` equals the request's `svix-id` header.
8. Replay the same delivery and confirm `{"processed": false}` with no duplicate user or event row.
9. Delete the temporary user after recording the result; do not use a predefined preview user for this test.

## Evidence to Record

For each failed scenario capture:

```text
scenario and identity
browser network status/body
KrakenD logs
FastAPI logs
Dramatiq logs when applicable
Clerk webhook attempt and event ID
sanitized relevant PostgreSQL rows
```
