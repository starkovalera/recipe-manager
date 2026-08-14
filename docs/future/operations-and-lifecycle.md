# Operations and Lifecycle Hardening

Stage: Captured

First-version scope: mixed; active roadmap requirements must be promoted explicitly

## Background processing and recovery

- Add retention and pruning for published transactional outbox rows. Define the retention period, bounded deletion batches, observability requirements, and any audit/history needs before removing successfully published records.
- Add a concurrent-dispatch claim or lease only if observed duplicate-delivery rates become operationally material. Preserve at-least-once delivery and idempotent consumers; do not introduce locking complexity without production evidence.
- Add operational metrics and alerts for transactional-outbox pending age, pending count, dispatch-failure count, and repeated-attempt count, with dimensions that avoid high-cardinality entity identifiers.
- In the background-jobs phase immediately after authentication work is complete, add scheduled invitation-expiration reconciliation. Find local invitations still marked `PENDING` whose `expires_at` is in the past and idempotently move them to `EXPIRED`, even when no `user.created` webhook arrives. Define batching, scheduling, concurrent-run protection, and diagnostics together with the other scheduled maintenance jobs.
- Add durable provider/local invitation reconciliation. Cover both divergence directions: the provider invitation remains active after local persistence and compensating revoke both fail, or the provider revoke succeeds while the local `PENDING → REVOKED` update fails. Decide whether to reconcile through provider status/list APIs, a transactional operation/outbox record, or both; keep retries idempotent and record sanitized diagnostics without persisting invitation tickets or URLs.
- Add a scheduled account-deletion recovery job that finds users which have remained `DELETION_PENDING` longer than an environment-backed stale threshold and idempotently republishes their account-deletion worker tasks. Protect concurrent scheduler runs, avoid duplicate active work where practical, log sanitized recovery diagnostics, and use the current runtime threshold rather than snapshotting it on each user. The user-deletion worker itself must remain idempotent so duplicate deliveries are safe.
- Add a scheduled recipe-deletion recovery job that finds recipes which have remained `DELETION_PENDING` longer than an environment-backed stale threshold and retries their media cleanup and physical database deletion. Use the current runtime threshold, process rows in bounded batches, define row-locking or claim behavior for concurrent runs, attempt every referenced media key, treat already-missing files idempotently, and leave the recipe pending when any cleanup step still fails. Record structured diagnostics without exposing these recipes through product APIs or search while recovery is pending.
- Reassess whether terminal import processing should continue its immediate best-effort primary-file cleanup or leave all primary artifacts to the scheduled retention lifecycle. P8B1 now safely finalizes retained leftovers as `FAILED_ARTIFACTS_REMOVED`, but changing the normal terminal path requires an explicit retention, cost, and product decision.
- Add destructive orphan cleanup only after operational evidence from the read-only `orphaned_upload_detection` reports. Require a safety delay, repeated confirmation across runs, bounded/idempotent deletion, protection against transient database failures, and coverage for orphaned recipe media left by failed deletion cleanup. Keep detection and deletion as separate operations.
- Add retention, access controls, and an optional admin API/UI for private maintenance reports. Reports currently remain storage-only system artifacts.

## Import operations and diagnostics

- Manual retry is currently allowed for every `FAILED` import while attempts remain, including failures such as `NOT_A_RECIPE` and `RECIPE_TOO_LONG`. Automatic retry classification is already explicit; revisit only whether manual retry eligibility should become more restrictive for deterministic failure details.
- Distinguish user-triggered and admin-triggered import retries and define notification policy for each case. A user-triggered retry creates an `IMPORT_STARTED` notification; an admin-triggered retry may require different recipient, visibility, and audit behavior.
- Consider explicitly associating each import `JobEvent` with a concrete attempt number so admin diagnostics can group lifecycle events by attempt without inferring boundaries from timestamps and `IMPORT_STARTED` events.

## Gateway and deployment

- Design centralized deployment configuration management for settings and environment variables consumed by multiple services, not only the backend. Define the source of truth and ownership for secrets versus non-secret configuration; how backend APIs, gateway, workers/Lambdas, scheduled jobs, and frontend build/runtime configuration receive consistent values; which settings may be changed safely without redeploying application artifacts; validation, versioning, rollout and rollback behavior; cache/refresh semantics; environment-specific overrides; auditability and access control; and failure behavior when configuration is missing, stale, or inconsistent across services.
- Replace KrakenD `input_query_strings: ["*"]` with explicit per-endpoint production query allowlists after the public API contract and deployment topology are finalized. Preserve repeated query parameters where the API supports them.
- Reassess and remove the local KrakenD `2.13.8` CORS `allow_headers` wildcard workaround before using the gateway configuration outside loopback development. Verify multi-header browser preflights against the selected production KrakenD version and use the narrowest working allowlist.
- If the FastAPI surface grows enough that maintaining the static KrakenD route list becomes error-prone, generate the static route objects from the OpenAPI contract in a build-time tool. Keep the committed config deterministic and retain the OpenAPI/config parity test as the enforcement boundary.

## Users and account lifecycle

- Add a durable webhook-conflict lifecycle and reconciliation workflow. Consider `PROCESSED` / `CONFLICT` states, sanitized conflict diagnostics, admin visibility, and an explicit replay operation instead of relying indefinitely on provider redelivery for persistent email collisions.
- Protect user synchronization from out-of-order `user.updated` webhook delivery. Store and compare a provider event timestamp or monotonic provider version before applying mutable identity fields so an older event cannot restore a previous email address.
- Optionally send the user a confirmation email only after asynchronous account cleanup has successfully removed all application-owned data. Define the sender, template, retry/idempotency behavior, and what happens when email delivery fails after deletion has already completed.

## Already active elsewhere

P11 hardening, P12 production artifacts, Terraform/IAM/secrets, technical production, and beta-readiness work belong to the active Development roadmap, not this Future Capability space. Reconciliation and recovery operations already delivered by P8A/P8B1 remain current contracts rather than future ideas.

## Refinement rule

Promote operational complexity only when a current release gate requires it or runtime evidence establishes the need. Preserve idempotency, bounded work, sanitized diagnostics, and explicit ownership in every promoted operation. Before creating a Development issue, identify the active roadmap gate or evidence that makes the work executable.
