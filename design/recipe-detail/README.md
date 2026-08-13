# Recipe Detail Design Workspace

Status: structural UX approved; Recipe Edit core partially complete; implementation handoff context preserved
Updated: 2026-08-13

This directory contains design artifacts only. Prototypes use local mock data and do not import production components or call application APIs.

## Start here

1. [`prototypes/00-decision-gallery/index.html`](prototypes/00-decision-gallery/index.html) — persistent visual gallery of approved Recipe Detail, global mobile shell, and Edit Mode decisions.
2. [`implementation-handoff.md`](implementation-handoff.md) — consolidated design-to-implementation context and evidence map for future GitHub issue slicing.
3. [`decisions/current-scope.md`](decisions/current-scope.md) — current boundary, completed work, remaining design work, and next gate.
4. [`decisions/07-edit-mode-current-decisions.md`](decisions/07-edit-mode-current-decisions.md) — approved Edit Mode structure, validation, guard, and remaining open work.
5. [`prototypes/16-mobile-edit-validation-and-guard/index.html`](prototypes/16-mobile-edit-validation-and-guard/index.html) — approved mobile Recipe Edit validation and guard evidence.
6. [`prototypes/17-desktop-edit-basics-validation-and-guard/index.html`](prototypes/17-desktop-edit-basics-validation-and-guard/index.html) — permanent desktop Basics, Ingredients, validation, and guard evidence.
7. [`decisions/11-global-mobile-shell.md`](decisions/11-global-mobile-shell.md) — default mobile top bar, global bottom navigation, and modal-layer contract for all screens.
8. [`decisions/06-approved-ux-foundation.md`](decisions/06-approved-ux-foundation.md) — consolidated approved Recipe Detail structure and behavior.
9. [`reusable-product-patterns.md`](reusable-product-patterns.md) — principles that may guide other Recipe Manager pages.
10. [`visual-execution-brief.md`](visual-execution-brief.md) — fixed inputs, open visual axes, and the future visual approval sequence.
11. [`decisions/14-temporary-artifact-consolidation-map.md`](decisions/14-temporary-artifact-consolidation-map.md) — map from temporary `.superpowers` working material to permanent handoff evidence.

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
| Prototype 11 | Expanded-versus-compact mobile Edit header | Historical comparison; compact-from-entry option C approved |
| Prototype 12 | Mobile Save placement | Top-toolbar Save approved; bottom accessory rejected |
| Prototype 13 | Integrated mobile Recipe Edit shell | Approved interactive baseline |
| Prototype 14 | Mobile Basics grid and compact Ingredients | Approved; mobile reordering removed |
| Prototype 15 | Touch-oriented Basics selection controls | Hybrid option A approved |
| Prototype 16 | Mobile validation, capacity errors, and unsaved guard | Approved low-fidelity behavior foundation |
| Prototype 17 | Desktop Basics, Ingredients, validation, and unsaved guard | Approved permanent low-fidelity behavior foundation |

## Current stage

The approved structural foundation is stable, but design is not complete. Remaining work includes Instructions, Cooking notes, Estimated nutrition, Manage Media, Organize Recipe, save request states, localized stress coverage, and the visual-direction stage. Do not slice production implementation issues for unfinished areas as though their UX were final.

## Working rules

- Do not overwrite approved iterations; create a new numbered iteration for material visual exploration.
- Do not use current production UI as a visual reference.
- Preserve approved UX while comparing visual directions.
- Use realistic sparse, normal, dense, flagged, error, and mobile states.
- Keep production implementation out of this directory and out of the current design phase.
