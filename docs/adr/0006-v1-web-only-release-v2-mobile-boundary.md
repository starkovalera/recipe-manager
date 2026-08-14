---
status: accepted
date: 2026-08-14
---

# V1 web-only release and V2 mobile planning boundary

## Decision

The first production release is **V1 Web Release** and is web-only. V1 is
complete only when the approved responsive-web product, required shared
contracts, technical production, operational web surfaces, security gates, and
beta-readiness evidence are complete.

The mobile client is **V2**. After V1 Web Release, the project runs a dedicated
mobile planning iteration that turns the existing native-client research,
shared API contracts, and any paired mobile Design evidence into an approved
mobile specification, requirements, and executable Development slices. All
mobile Development work is V2, including native architecture, build/release,
mobile authentication, offline/background/push decisions, and client
implementation.

Design work may still be paired: a shared contract can generate `[WEB]` and
`[MOBILE]` Design children under one product context. The mobile child is
non-blocking for the V1 web handoff and may be completed early or deferred. A
paired Design artifact does not authorize mobile Development.

## Consequences

- V1 release graphs and acceptance criteria must not depend on Mobile Beta.
- The V1 Design gate covers shared product meaning and responsive-web behavior;
  mobile-specific Design and reconciliation have a separate V2 gate.
- The native-client decision packet remains useful evidence, but its provisional
  recommendation is not an owner approval or a V1 commitment.
- Shared API/backend work can remain cross-client when it is needed by V1 web;
  that does not pull mobile implementation into V1.
- GitHub `v1` and `v2` labels identify release target and remain separate from
  canonical readiness labels.

## Related records

- [ADR-0004 — Gate production UI implementation on the Core Design Baseline](0004-design-baseline-gates-ui-implementation.md)
- [Project roadmap](../roadmap.md)
- [Product Design roadmap](../../design/roadmap.md)
- [Production roadmap](../architecture/production-roadmap.md)
- [Issue #27 — V2 native client architecture input](https://github.com/starkovalera/recipe-manager/issues/27)
