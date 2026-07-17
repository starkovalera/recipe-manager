# Recipe Manager Production Roadmap

## Phase 0 — Stable Main and CI Baseline

- Record production architecture and completed auth testing.
- Add backend, frontend, and gateway CI.
- Verify Alembic against clean PostgreSQL + pgvector.
- Merge the current baseline branch.
- Use `main` as the default integration branch.
- Enable required checks.
- Create `v0.1.0-local-baseline`.

## Phase 1 — Local Production Readiness

Implementation details and acceptance criteria for each subphase are agreed
immediately before that subphase starts.

P5-P8 establish the import, embedding, account-deletion, and maintenance
entrypoints for the four production Lambdas.

- **P1. PROD settings fail closed**
- **P2. QueuePublisher protocol and preview Dramatiq adapter**
- **P3. Transactional outbox**
- **P4. SQS publisher**
- **P5. Import Lambda adapter**
- **P6. Embedding Lambda adapter**
- **P7. Account-deletion Lambda adapter**
- **P8. Maintenance dispatcher**
- **P9. S3 storage provider**
- **P10. Presigned media access**
- **P11. SSRF and streaming hardening**
- **P12. Production Docker artifacts**

Iteration 1 covers P1 and P2 only: production configuration requires explicit PostgreSQL, SQS, and S3 selections, while PREVIEW publishes ID-only messages through the existing Dramatiq actors. The SQS and S3 values define the target configuration contract; their runtime adapters remain deferred to P4 and P9. P3, the transactional outbox, is not part of this iteration.

## Phase 2 — Terraform, IAM, and Secrets Foundation

- Bootstrap remote Terraform state and GitHub OIDC.
- Provision ECR, SQS/DLQ, Lambda, EventBridge, S3, IAM, logs, alarms, budgets, compute, and network boundaries.
- Manage secret containers, references, KMS, and IAM through Terraform.
- Keep secret values outside Terraform state.
- Decide and document the Lightsail or EC2 deployment mechanism.

## Phase 3 — Technical Production and CD

- Provision AWS, Neon, Cloudflare, Clerk production, Flagsmith, DNS, and TLS.
- Add independent deployment workflows.
- Deploy immutable artifacts for an exact `main` commit.
- Run controlled migrations.
- Execute production smoke tests and rollback rehearsal.
- Keep access limited to internal test users.

## Phase 4 — Frontend Redesign / Rewrite

- Keep React/Vite SPA and the existing API contracts.
- Preserve reusable Clerk bootstrap, API client, types, and TanStack Query integration where appropriate.
- Redesign the application shell, navigation, responsive pages, forms, errors, loading states, empty states, accessibility, and PWA experience.
- Validate against real S3, SQS, Lambda, Clerk, and production latency/failure behavior.

## Phase 5 — Beta Readiness

- Complete security, privacy, accessibility, restore, incident, DLQ, secret-rotation, monitoring, and cost-control reviews.
- Run complete product E2E tests.
- Invite external beta users only after this phase passes.

## Phase boundaries

Do not combine Phase 0 with production infrastructure implementation.
Do not combine all Phase 1 items into one pull request.
Do not invite external beta users before Phases 4 and 5 are complete.
