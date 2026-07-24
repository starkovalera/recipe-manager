# Recipe Detail Design Workspace

Status: structural UX approved; ready for visual-direction exploration  
Updated: 2026-07-24

This directory contains design artifacts only. Prototypes use local mock data and do not import production components or call application APIs.

## Start here

1. [`prototypes/00-decision-gallery/index.html`](prototypes/00-decision-gallery/index.html) — persistent visual gallery of approved Recipe Detail, global mobile shell, and Edit Mode decisions.
2. [`decisions/11-global-mobile-shell.md`](decisions/11-global-mobile-shell.md) — default mobile top bar, global bottom navigation, and modal-layer contract for all screens.
3. [`prototypes/10-mobile-global-navigation/index.html`](prototypes/10-mobile-global-navigation/index.html) — interactive approved mobile application shell.
4. [`decisions/07-edit-mode-current-decisions.md`](decisions/07-edit-mode-current-decisions.md) — approved Edit Mode structure and remaining open work.
5. [`decisions/06-approved-ux-foundation.md`](decisions/06-approved-ux-foundation.md) — consolidated approved Recipe Detail structure and behavior.
6. [`reusable-product-patterns.md`](reusable-product-patterns.md) — principles that may guide other Recipe Manager pages.
7. [`visual-execution-brief.md`](visual-execution-brief.md) — fixed inputs, open visual axes, and the next approval sequence.
8. [`prototypes/05-main-actions-and-responsive-panels/index.html`](prototypes/05-main-actions-and-responsive-panels/index.html) — current desktop behavior prototype.

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
| Prototype 06 | Complete mobile Recipe Detail reading, Focus, Media, Import Info, and responsive header | Approved mobile Recipe Detail foundation |
| Prototype 10 | Global mobile top and bottom navigation with a single modal-layer interaction | Approved product-wide mobile shell; visual refinement pending |
| Edit Mode working set | Editing navigation, auxiliary panels, Manage Media, and Unit selector | Current approved structural direction; consolidated in the decision gallery |

## Working rules

- Do not overwrite approved iterations; create a new numbered iteration for material visual exploration.
- Do not use current production UI as a visual reference.
- Preserve approved UX while comparing visual directions.
- Use realistic sparse, normal, dense, flagged, error, and mobile states.
- Keep production implementation out of this directory and out of the current design phase.
