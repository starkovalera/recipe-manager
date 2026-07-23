# Recipe Detail Design Workspace

Status: structural UX approved; ready for visual-direction exploration  
Updated: 2026-07-23

This directory contains design artifacts only. Prototypes use local mock data and do not import production components or call application APIs.

## Start here

1. [`decisions/06-approved-ux-foundation.md`](decisions/06-approved-ux-foundation.md) — consolidated approved Recipe Detail structure and behavior.
2. [`reusable-product-patterns.md`](reusable-product-patterns.md) — principles that may guide other Recipe Manager pages.
3. [`visual-execution-brief.md`](visual-execution-brief.md) — fixed inputs, open visual axes, and the next approval sequence.
4. [`prototypes/05-main-actions-and-responsive-panels/index.html`](prototypes/05-main-actions-and-responsive-panels/index.html) — current behavior prototype.
5. [`reviews/05-main-actions-and-responsive-panels/`](reviews/05-main-actions-and-responsive-panels/) — latest UX, visual, product-fit, accessibility, and responsive critiques.

Historical artifacts remain evidence, not current alternatives. When they conflict, the approved foundation and `docs/ui-ux/07-decisions-log.md` win.

## Artifact map

```text
research/      Current interface references and extracted principles
wireframes/    Early isolated comparisons and rationale
prototypes/    Browser-rendered behavior iterations with mock data
screenshots/   Reproducible viewport and state evidence
reviews/       Separate critique passes for every prototype iteration
decisions/     Scope, approved comparisons, and consolidated foundation
```

## Iteration trail

| Iteration | Purpose | Status |
| --- | --- | --- |
| Wireframe 01 | Flagged-entry behavior | Historical comparison; Default View status approved |
| Wireframes 02–03 | Difficulty/rating and metadata order | Historical comparison; B2 approved |
| Prototype 01 | Initial structure and state coverage | Superseded behavior evidence |
| Prototype 02 | Feedback refinement | Superseded behavior evidence |
| Prototype 03 | Panel and resource hierarchy | Incorporated into v5 |
| Prototype 04 | Icon, width, and consequence control | Incorporated into v5 |
| Prototype 05 | Main actions, responsive panels, resources, and deletion | Current approved low-fidelity behavior foundation |

## Working rules

- Do not overwrite approved iterations; create a new numbered iteration for material visual exploration.
- Do not use current production UI as a visual reference.
- Preserve approved UX while comparing visual directions.
- Use realistic sparse, normal, dense, flagged, error, and mobile states.
- Keep production implementation out of this directory and out of the current design phase.
