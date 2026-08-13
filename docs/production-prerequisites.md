# Production Prerequisites

Updated: 2026-08-13
Status: not audited with the project owner

This checklist records decisions and external setup that an agent cannot safely infer or complete without owner authority. Existing accounts or projects may satisfy an item; verify before creating anything.

Record identifiers, regions, project names, resource names, secret-store references, and verification evidence. Keep credentials, tokens, connection strings, and secret values in approved local or provider secret storage.

## Refinement decisions

- [ ] Select Terraform or OpenTofu for the production infrastructure workflow.
- [ ] Select the AWS account model and primary production region.
- [ ] Select the remote state and locking bootstrap approach.
- [ ] Decide the Lightsail or EC2 deployment mechanism for FastAPI and KrakenD.
- [ ] Select the native mobile client stack after the architecture decision packet is reviewed.
- [ ] Confirm the production domain and DNS ownership model.

These items remain `needs-triage` until the decision, rationale, and acceptance boundary are recorded.

## Owner-controlled external setup

### AWS

- [ ] Confirm or create the production AWS account.
- [ ] Enable owner MFA, billing contacts, and cost/budget notifications.
- [ ] Confirm the primary region and resource-name prefix.
- [ ] Authorize the bootstrap mechanism for Terraform state and GitHub OIDC.
- [ ] Provide an approved local AWS profile or equivalent temporary authorization for live verification.

### Application providers

- [ ] Confirm or create the Neon production project and approved secret reference.
- [ ] Confirm or create the Clerk production instance, invitation policy, webhook endpoint plan, and secret references.
- [ ] Confirm or create the Cloudflare account, production domain, DNS zone, and Pages project.
- [ ] Confirm or create the Flagsmith production project/environment and secret references.
- [ ] Confirm or create the OpenAI production project, billing boundary, limits, and secret reference.
- [ ] Confirm or create frontend and server-side Sentry projects, privacy settings, and DSN secret references.

### Delivery control

- [ ] Define GitHub production environment approvers and protection rules.
- [ ] Confirm where production secret values are stored and who may rotate them.
- [ ] Confirm the owner for migration approval, rollback authorization, incident contact, and cost alerts.

An item is `ready-for-human` when its exact owner action and expected unblock evidence are known. After the owner records that evidence, create or unblock the corresponding agent issue; do not copy this whole checklist into every issue.
