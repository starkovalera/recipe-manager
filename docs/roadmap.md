# Recipe Manager Roadmap

Updated: 2026-08-18<br>
Audience: human project planning

This is the canonical human-facing project overview. It shows the major work blocks, their status, the order in which results become available, and links to the documents that own the detail. It is intentionally concise: product decisions, technical contracts, and executable issue bodies remain in their subject documents and GitHub.

## Source-of-truth hierarchy

1. This document defines the project-scale Design and Development work graph and release outcomes.
2. [`design/roadmap.md`](../design/roadmap.md) owns detailed Design scope, domain status, and baseline gates.
3. [`architecture/production-roadmap.md`](architecture/production-roadmap.md) owns detailed Development phases, readiness, and implementation gates.
4. [`architecture/production-architecture.md`](architecture/production-architecture.md) owns the target production topology and its unresolved architecture decisions.
5. GitHub issues are the executable work queue; native issue dependencies are the source of truth for blockers.
6. [`future/`](future/README.md) holds capabilities that are not active V1 work; the V2 mobile track is documented separately as a deferred release sequence.
7. [`archive/`](archive/README.md) preserves superseded plans and historical snapshots.

The roadmap summarizes its source documents rather than copying their contracts. Agent workflow and issue-writing rules remain in the agent documentation and are deliberately outside this human-facing map.

## Global tracks

| Track | Current state | Current destination |
| --- | --- | --- |
| `[DESIGN]` | Core Design Baseline v1 in progress | Approve shared product contracts, complete the V1 responsive-web design, record paired mobile design evidence where useful, and approve the V1 web implementation handoff |
| `[DEV]` | Local baseline, P1-P10 runtime boundaries, and the P11 hardening specification complete; #23 closed; P11 Children A-B implemented, with Child B in review and Child C next after merge; technical production in progress | Finish P11 implementation, artifacts, infrastructure, deployment, approved web client, operational surfaces, and Public v1 gates; start mobile only in the post-V1 V2 track |

Design and Development proceed in parallel. Production UI implementation is gated by the applicable approved Design baseline; backend, infrastructure, contract discovery, and other non-visual work may proceed earlier when their own blockers are closed.

## Release sequencing

V1 is the first production release and is **web-only**. Its release gate is the
approved V1 web Design handoff plus technical production, operational surfaces,
security, and beta-readiness evidence. Paired mobile Design work may run in the
same product context, but its completion and every mobile Development task are
outside the V1 release gate.

V2 starts after V1 Web Release with a dedicated mobile planning iteration. That
iteration turns the deferred mobile architecture packet, shared contracts, and
paired Design evidence into an approved mobile specification and executable
Development issues. Use the orthogonal GitHub labels `v1` and `v2` together
with the canonical triage labels; the version label identifies release target,
not readiness.

## Release outcomes

| Milestone | Human-readable result |
| --- | --- |
| Core Design Baseline v1 | Approved shared product meaning and V1 responsive-web behavior, difficult states, accessibility/localization coverage, and the web implementation handoff; paired mobile evidence is non-blocking |
| Internal Web Beta | Technical production plus the approved responsive-web Core client is operational for internal users |
| Operational Surfaces Addendum v1 | Admin, debug, and operational web contracts required for the V1 public release are approved; mobile operational design may be paired or deferred |
| Public v1 | Stable web, implemented V1 operational surfaces, passed security and beta-readiness gates, and recorded release evidence |
| V2 Mobile Planning | After Public v1, the mobile specification, requirements, design gate, and executable Development slices are approved |
| V2 Mobile Beta | Technical production plus the approved V2 native-mobile Core client is operational |

## Cross-track dependency map

```mermaid
flowchart LR
  designCore["Core Design Baseline v1"] --> webCore["Approved responsive-web Core"]
  designCore -. paired, non-blocking .-> mobileDesign["Paired/deferred mobile Design evidence"]
  designOps["Operational Surfaces Addendum v1"] --> opsClients["Operational surfaces implementation"]

  techProd["Technical production"] --> webBeta["Internal Web Beta"]
  webCore --> webBeta

  webBeta --> publicV1["Public v1"]
  opsClients --> publicV1
  beta["Beta-readiness and release evidence"] --> publicV1

  publicV1 --> v2Planning["V2 mobile planning iteration"]
  mobileDesign -. informs .-> v2Planning
  mobileResearch["#27 V2 native architecture input"] -. informs .-> v2Planning
  v2Planning --> mobileCore["Approved V2 native-mobile Core"]
  techProd -. reused after V1 .-> mobileBeta["V2 Mobile Beta"]
  mobileCore --> mobileBeta
```

The Operational Addendum does not block V1 Core web implementation. It blocks Public v1 through its implementation and release evidence. Public v1 is the solid sequencing gate for V2 planning; paired mobile Design evidence and #27 are dashed inputs until that planning iteration creates approved mobile scope and blockers.

## Design track

Source of truth: [`Product Design Roadmap`](../design/roadmap.md). Tracker: [#29 — Core Design Baseline v1](https://github.com/starkovalera/recipe-manager/issues/29).

The graph uses one node for each logically independent Design Domain. Each
domain is refined as a shared product contract, a V1 responsive-web result, and
an optional paired native-mobile result. Shared/web reconciliation is part of
the V1 handoff; mobile-specific reconciliation is useful evidence but does not
block V1.

```mermaid
flowchart TD
  foundation["✓ Shared design foundation and Recipe Detail structural foundation"]
  scope["✓ #20 Scope and decision inventory<br/>published evidence packet"]
  constraints["#22 API, schema, and platform constraints<br/>ready frontier"]
  recipeFacts["#21 Recipe Detail/Edit contract facts<br/>ready frontier"]

  auth["Auth, invitations, and onboarding<br/>shared + V1 web + paired mobile"]
  recipes["Recipe library, detail, edit, and search<br/>shared + V1 web + paired mobile"]
  imports["Import journeys<br/>shared + V1 web + paired mobile"]
  collections["Collections and tags<br/>shared + V1 web + paired mobile"]
  notifications["Notifications<br/>shared + V1 web + paired mobile"]
  account["Profile and account<br/>shared + V1 web + paired mobile"]

  integration["Cross-domain shared + V1 web integration"]
  mobileEvidence["Paired/deferred mobile Design evidence<br/>non-blocking for V1"]
  operational["Operational Surfaces Addendum v1<br/>deferred, non-blocking for Core"]
  result["Result: approved V1 Web Core Design Baseline<br/>with implementation handoff"]

  foundation -. existing evidence .-> scope
  foundation -. existing evidence .-> constraints
  scope --> auth
  scope --> recipes
  scope --> imports
  scope --> collections
  scope --> notifications
  scope --> account
  constraints --> auth
  constraints --> recipes
  constraints --> imports
  constraints --> collections
  constraints --> notifications
  constraints --> account
  recipeFacts --> recipes

  auth --> integration
  recipes --> integration
  imports --> integration
  collections --> integration
  notifications --> integration
  account --> integration
  integration --> result
  auth -. paired mobile evidence .-> mobileEvidence
  recipes -. paired mobile evidence .-> mobileEvidence
  imports -. paired mobile evidence .-> mobileEvidence
  collections -. paired mobile evidence .-> mobileEvidence
  notifications -. paired mobile evidence .-> mobileEvidence
  account -. paired mobile evidence .-> mobileEvidence
  scope -. later non-blocking work .-> operational

  classDef complete fill:#dcfce7,stroke:#15803d,color:#14532d
  classDef ready fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
  classDef planned fill:#fef3c7,stroke:#d97706,color:#78350f
  classDef blocked fill:#fee2e2,stroke:#dc2626,color:#7f1d1d
  classDef deferred fill:#e5e7eb,stroke:#6b7280,color:#374151
  classDef result fill:#ede9fe,stroke:#7c3aed,color:#4c1d95

  class foundation complete
  class scope,constraints,recipeFacts ready
  class auth,recipes,imports,collections,notifications,account planned
  class integration blocked
  class operational deferred
  class result result
```

### Design result

The Design track's V1 result is an approved shared product contract and
responsive-web handoff detailed enough to implement without treating
prototypes as production source. Paired mobile evidence may be available, but
the V1 Core baseline is not blocked by completing mobile Design. The V2 mobile
client receives a separate planning and design gate after V1; the Operational
Addendum remains required before Public v1.

## Development track

Source of truth: [`Production Roadmap`](architecture/production-roadmap.md). Tracker: [#32 — Public v1 delivery tracker](https://github.com/starkovalera/recipe-manager/issues/32).

```mermaid
flowchart TD
  phase0["✓ Phase 0: stable main and CI baseline"]
  runtime["✓ P1-P10 runtime boundaries"]

  p11["✓ #23 P11 hardening specification (closed)"]
  p11Implementation["#37 ✓; #38 ✓ (in review); #39 → #40 P11 implementation"]
  p12["✓ #25 P12 production artifact matrix"]
  localstack["#26 LocalStack + Preview acceptance closure"]
  liveAws["#59 Live AWS S3/provider verification"]
  frontendAudit["#24 Reusable non-visual frontend contracts"]
  mobileResearch["#27 V2 native client architecture input"]
  infraRefine["#31 Terraform/OpenTofu and AWS foundation refinement"]
  owner["#30 Owner-controlled production prerequisites"]

  infra["Provisioned infrastructure, providers, deployment, and observability"]
  candidate["Exact production release candidate"]
  security["#28 Security audit and remediation"]
  technical["Technical production deployment, smoke, and rollback"]

  design["#29 Core Design Baseline v1"]
  web["Approved responsive-web implementation"]
  mobile["V2 approved native-mobile implementation"]
  webBeta["Internal Web Beta"]
  designOps["Operational Surfaces Addendum v1"]
  ops["Operational web implementation<br/>mobile pairing may defer"]
  beta["Beta-readiness and release evidence"]
  result["Result: Public v1<br/>stable web, production operations, security, and release evidence"]
  v2Planning["V2 mobile planning iteration<br/>after Public v1"]
  mobileBeta["V2 Mobile Beta"]

  phase0 --> runtime
  runtime --> p11
  runtime --> p12
  runtime --> localstack
  runtime --> infraRefine
  owner -. owner inputs .-> infraRefine
  infraRefine --> infra
  owner --> infra
  owner --> liveAws
  p12 --> infra

  p11 --> p11Implementation
  p11Implementation --> candidate
  p12 --> candidate
  infra --> candidate
  localstack --> candidate
  candidate --> security
  security --> technical
  liveAws --> technical

  design --> web
  design -. paired mobile Design evidence .-> v2Planning
  frontendAudit -. informs .-> web
  mobileResearch -. V2 input .-> v2Planning
  technical --> webBeta
  web --> webBeta
  designOps --> ops

  webBeta --> result
  ops --> result
  beta --> result
  result --> v2Planning
  v2Planning --> mobile
  technical -. reused after V1 .-> mobileBeta
  mobile --> mobileBeta

  classDef complete fill:#dcfce7,stroke:#15803d,color:#14532d
  classDef ready fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
  classDef refine fill:#fef3c7,stroke:#d97706,color:#78350f
  classDef blocked fill:#fee2e2,stroke:#dc2626,color:#7f1d1d
  classDef gated fill:#fce7f3,stroke:#db2777,color:#831843
  classDef deferred fill:#e5e7eb,stroke:#6b7280,color:#374151
  classDef result fill:#ede9fe,stroke:#7c3aed,color:#4c1d95

  class phase0,runtime complete
  class p11,p12,localstack complete
  class p11Implementation,frontendAudit ready
  class liveAws,infraRefine,owner refine
  class infra,candidate,security,technical blocked
  class design,web,webBeta,designOps,ops,beta gated
  class mobileResearch,v2Planning,mobile,mobileBeta deferred
  class result result
```

Issue [#23](https://github.com/starkovalera/recipe-manager/issues/23) is closed: merged PR [#49](https://github.com/starkovalera/recipe-manager/pull/49) delivered the complete P11 specification and child-issue graph. Child A [#37](https://github.com/starkovalera/recipe-manager/issues/37) is complete in merged [PR #63](https://github.com/starkovalera/recipe-manager/pull/63); Child B [#38](https://github.com/starkovalera/recipe-manager/issues/38) is implemented and in review on the current branch; the remaining implementation gate is [#39](https://github.com/starkovalera/recipe-manager/issues/39) → [#40](https://github.com/starkovalera/recipe-manager/issues/40) after #38 merges, with native blockers preserved.

The P12 artifact matrix in [#25](https://github.com/starkovalera/recipe-manager/issues/25) is complete in merged PR [#52](https://github.com/starkovalera/recipe-manager/pull/52). It defines six production image artifacts, shared packaging and runtime invariants, compatibility triggers, release identity, rollback rules, and the independently verifiable implementation children [#41](https://github.com/starkovalera/recipe-manager/issues/41)–[#47](https://github.com/starkovalera/recipe-manager/issues/47). Those implementation children remain the active P12 work.

LocalStack and Preview acceptance for [#26](https://github.com/starkovalera/recipe-manager/issues/26) is recorded in draft PR [#58](https://github.com/starkovalera/recipe-manager/pull/58). The real-provider boundary is intentionally separate in [#59 — Verify Live AWS S3 media access boundaries](https://github.com/starkovalera/recipe-manager/issues/59): [#30](https://github.com/starkovalera/recipe-manager/issues/30) is its owner-input blocker, and #59 gates technical production smoke without blocking #31 refinement or the other independent Phase 1 work.

### Development result

The Development track ends its current V1 sequence with Public v1: a
deployable and operated production system, an approved responsive-web client,
implemented V1 operational surfaces, a passed release-candidate security gate,
and recorded beta-readiness/release evidence. Technical production alone
produces internal infrastructure and does not constitute a product beta. The
native-mobile client is a separate V2 outcome that starts with post-V1
planning.

### Target architecture at roadmap end

The source-of-truth architecture diagram is maintained in [`Production Architecture — roadmap end-state view`](architecture/production-architecture.md#roadmap-end-state-view). The logical topology is sufficiently known to draw now: web and mobile use one API boundary, FastAPI owns domain authorization, queues and Lambdas own durable background work, Neon owns durable relational state, S3 owns private media, and Clerk/Flagsmith provide cross-cutting services.

The target architecture remains cross-client, but V1 does not depend on the
native client. The native stack and delivery decision ([#27](https://github.com/starkovalera/recipe-manager/issues/27)) is a V2 input to revisit after V1; Terraform/OpenTofu plus the Lightsail/EC2 deployment mechanism ([#31](https://github.com/starkovalera/recipe-manager/issues/31)) and owner-provided cloud/account/domain/secret prerequisites ([#30](https://github.com/starkovalera/recipe-manager/issues/30)) remain current V1 infrastructure decisions. Those open decisions are shown explicitly in the architecture source instead of being guessed here. Separately, [#59](https://github.com/starkovalera/recipe-manager/issues/59) validates the real AWS provider boundary after #30; it is a production gate, not a topology decision or a blocker for #31 refinement.

## Human-facing project documents

| Document | Use |
| --- | --- |
| [`CONTEXT.md`](../CONTEXT.md) | Shared product language and project-level planning vocabulary |
| [`Product Design Roadmap`](../design/roadmap.md) | Design Domains, baseline gates, and Design readiness |
| [`Production Roadmap`](architecture/production-roadmap.md) | Development phases, runtime readiness, and delivery gates |
| [`Production Architecture`](architecture/production-architecture.md) | Selected topology, boundaries, target end-state, and open infrastructure decisions |
| [`Production prerequisites`](production-prerequisites.md) | Human-owned accounts, provider setup, and external inputs |
| [`V1/V2 release boundary ADR`](adr/0006-v1-web-only-release-v2-mobile-boundary.md) | Accepted sequencing rule: V1 web-only, V2 mobile after post-V1 planning |
| [`Future Capabilities`](future/README.md) | Product ideas, technical debt, and intentional deferrals outside active scope |
| [`Shared product scope`](../design/shared/product-scope.md) | Human-readable cross-product scope and V1/V2 boundaries |
| [`Recipe Detail current scope`](../design/recipe-detail/decisions/current-scope.md) | Human-readable Design Domain decisions and remaining Recipe Detail work |
| [`API documentation`](api.md) | Current API contracts and integration-facing behavior |

## Keeping this roadmap current

After a work block or its executable issue changes status, especially after a
merged pull request:

1. update the owning detailed roadmap or architecture document;
2. update the corresponding node and status in this overview, marking completed blocks with `✓` and recording the concrete result;
3. revise the graph when a real dependency, outcome, or release gate changes;
4. update the target architecture diagram when an open architecture decision closes;
5. refresh task links, status references, and open questions in the affected documents;
6. keep GitHub issue bodies and native blocker edges authoritative for execution details; close the issue only when its own acceptance criteria and required scope are complete, leaving unfinished child work tracked separately.

The task lifecycle requires this synchronization before completion is handed off.
This document is the human-readable project map, not a second issue tracker.
