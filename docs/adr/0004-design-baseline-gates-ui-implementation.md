---
status: accepted
---

# Gate production UI implementation on the Core Design Baseline

Production client UI implementation begins only after the applicable approved
Design baseline. For V1, that means the responsive-web Core Design Baseline:
the first production release is web-only. Paired mobile Design work may be
created in the same product context and may inform later decisions, but mobile
Design completion is not a V1 gate and no mobile Development work follows from
the Design artifact alone.

V2 mobile UI begins only after the post-V1 mobile planning iteration approves
the mobile specification, requirements, and applicable mobile Design/
reconciliation evidence. Admin, debug, and operational Design may finish later
as an Operational Surfaces Addendum, allowing V1 Core web implementation to
proceed while keeping the required V1 operational web surfaces as a public-
release requirement. This sequencing amendment is recorded in
[ADR-0006](0006-v1-web-only-release-v2-mobile-boundary.md).
