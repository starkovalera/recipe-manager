# Operations and Lifecycle Hardening

Stage: Captured
First-version scope: mixed; active roadmap requirements must be promoted explicitly

## Opportunities

- published-outbox retention and pruning;
- a concurrent dispatch lease only if duplicate-delivery evidence justifies it;
- outbox age/count/failure metrics and alerts;
- invitation provider/local reconciliation;
- evidence-driven destructive orphan cleanup after repeated read-only reports;
- maintenance-report retention, access controls, and optional API/UI;
- more restrictive manual retry eligibility;
- user/admin retry attribution and notification policy;
- attempt numbers on Import Job events;
- centralized deployment configuration ownership and rollout;
- explicit KrakenD query allowlists and narrower production CORS;
- generated deterministic gateway routes if route maintenance becomes costly;
- webhook conflict lifecycle and out-of-order provider-event protection;
- post-deletion confirmation email.

## Already active elsewhere

P11 hardening, P12 production artifacts, Terraform/IAM/secrets, technical production, and beta-readiness work belong to the active Development roadmap, not this Future Capability space. Reconciliation and recovery operations already delivered by P8A/P8B1 remain current contracts rather than future ideas.

## Refinement rule

Promote operational complexity only when a current release gate requires it or runtime evidence establishes the need. Preserve idempotency, bounded work, sanitized diagnostics, and explicit ownership in every promoted operation.
