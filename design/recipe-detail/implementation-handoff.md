# Recipe Detail Design-to-Implementation Handoff Context

Status: intermediate approved design context; prepared for future GitHub issue slicing
Updated: 2026-08-13

## Purpose

This document gives a future planning agent one stable entry point for turning completed Recipe Detail design into implementation-ready GitHub issues. It is not itself an implementation plan and does not authorize production changes.

Issue slicing must distinguish:

- approved behavior that is ready to specify;
- feature-level design that remains incomplete;
- final visual tokens and treatments that have not yet been selected;
- backend or schema work that must be verified rather than inferred from prototypes.

## Source-of-truth order

When artifacts conflict, use this order:

1. `decisions/decision-log.md` — latest explicit approvals and supersessions;
2. `decisions/current-scope.md` — current boundary and remaining work;
3. numbered decision files, especially `06`, `07`, `11`, `12`, and `13`;
4. approved prototype README and review files;
5. the prototype behavior and screenshots;
6. historical comparisons only as rationale, never as current requirements.

The promotion record for temporary session material is `decisions/14-temporary-artifact-consolidation-map.md`.

Production JSX/CSS is not a design reference. Prototype code is behavior evidence and must be reimplemented using production architecture, accessibility primitives, data contracts, and tests.

## Product and draft boundaries

```text
Saved Recipe
├── Default View / Cooking Focus
├── Recipe Edit draft
├── Manage Media draft
├── Organize Recipe context
└── Auxiliary context (one slot)
    ├── Media — read only
    └── Import Info — immediate resource/review actions
```

- Recipe Edit Save persists the recipe-content draft as one unit.
- Opening Media or Import Info preserves the Recipe Edit draft, active section, and scroll position.
- Import Info resource removal and `Mark all reviewed` are immediate actions and are not rolled into Recipe Edit Save.
- Entering Manage Media leaves Recipe Edit and triggers the dirty-draft guard when necessary.
- Manage Media has its own Save/Cancel boundary.
- Recipe deletion is a separate irreversible recipe action.

## Approved implementation slices and evidence

These are coherent future issue domains, not final issue titles or dependency estimates.

| Domain | Approved contract | Primary evidence | Readiness |
| --- | --- | --- | --- |
| Recipe Detail shell and Default View | Compact header, corrected-B action band, metadata order, bounded content, desktop columns | `decisions/06-approved-ux-foundation.md`, Prototype 05 | Structurally ready; visual styling pending |
| Cooking Focus | Simplified content, preserved navigation, intentional mobile Ingredients/Instructions switch | Prototype 05 and Prototype 06 | Structurally ready; visual styling pending |
| Global mobile shell | Hierarchy-aware top bar, five-item navigation, one modal layer | `decisions/11-global-mobile-shell.md`, Prototype 10 | Ready as shared shell contract |
| Media auxiliary panel | Images and understandable external links, one auxiliary slot, state preservation | Prototype 05 and Prototype 06 | Structurally ready |
| Import Info panel | Flags, Mark all reviewed, primary/derived groups, ignored resources, thumbnails, inline irreversible removal | `decisions/06-approved-ux-foundation.md`, Prototypes 03–05 | Structurally ready; backend capabilities must be verified |
| Recipe deletion | Overflow-only entry, blocking confirmation, no Undo, explicit imported-resource consequence | Prototype 05 | Structurally ready |
| Desktop Recipe Edit shell | Continuous page, sticky rail, scrollspy, one recipe draft and Save/Cancel pair | `decisions/13-desktop-edit-basics-validation-and-entry-behavior.md`, Prototype 17 | Ready for Basics/Ingredients scope |
| Mobile Recipe Edit shell | Compact Back/title/Save/Overflow, global navigation, single-open accordion | `decisions/12-mobile-edit-shell-and-save-action.md`, Prototypes 12–13 | Ready |
| Basics editing | Fixed Source, compact numeric fields, positive-whole Cooking time/Servings, direct Difficulty, whole-star Rating | Prototypes 14–17, decision files `07` and `13` | Ready; persistence support must be verified |
| Ingredients editing | 50-item limit, fixed Unit, desktop reorder, compact mobile rows and single-item sheet | Prototypes 14–17, decision files `07` and `13` | Ready except exact Unit dictionary |
| Validation and dirty guard | Hybrid timing, linked summary, error counts, local ingredient errors, desktop dialog, mobile sheet | Prototypes 16–17 and their reviews, decision files `07` and `13` | Approved behavior |

## Superseded behavior that must not become requirements

- Do not use a permanent desktop `Import info` action in the main action band; desktop uses Overflow.
- Do not reopen Import Info every time the user changes View/Focus/Edit. Auto-open occurs once on first entry to a flagged recipe visit.
- Do not use the earlier flagged Default View status as the only entry behavior when auto-open applies.
- Do not use expanded mobile Recipe identity at Edit entry.
- Do not add a fixed mobile `Cancel / Save changes` bar or a dirty-state accessory above global navigation.
- Do not add mobile ingredient DnD, reorder handles, or move commands.
- Do not use generic mobile dropdowns for all Basics selections; use the approved hybrid treatment.
- Do not use field-level conflict resolution for import flags; flags are general messages and use `Mark all reviewed`.
- Do not duplicate extracted recipe content inside Import Info.
- Do not add Media/Import Info switching inside either panel.

## Cross-cutting acceptance contracts

Every future issue touching these surfaces must account for:

- keyboard focus and focus restoration;
- background inertness and focus trapping for blocking layers;
- Escape, cross, backdrop, system Back, and swipe behavior where approved;
- safe-area insets and at least 44 px mobile targets;
- no horizontal overflow at 360, 390, and 430 CSS px;
- screen-reader names for icon-only actions;
- non-color-only errors, destructive meaning, status, and selection;
- preservation of draft, mode, active section, panel state, and scroll position across auxiliary panels;
- browser Back behavior, including dirty-draft protection;
- sparse, normal, dense, flagged, loading, failure, and unavailable states;
- localization pressure and long labels;
- role-gated debug information in Import Info.

## Data and backend questions to verify before issue creation

Do not invent these contracts from mock data. Inspect the current production schemas and APIs when implementation planning begins:

- persistence support for Difficulty and Personal rating;
- Source enum values and localization ownership;
- Unit dictionary, aliases, ordering, and canonical stored value;
- exact field maximum lengths;
- ingredient and instruction ordering/stable identity;
- import flag bulk-review mutation;
- primary/derived resource relationship payloads;
- ignored/removed resource summaries and removal consequences;
- current-cover exception during primary-resource deletion;
- media capacity and upload constraints;
- save concurrency, server validation, retry, and conflict behavior;
- role checks for debug import details.

## Not ready for implementation issue slicing

The following areas require additional design first:

- Instructions editing and validation;
- Cooking notes editing and validation;
- Estimated nutrition editing and validation;
- detailed Manage Media desktop/mobile workspace;
- detailed Organize Recipe behavior;
- save request progress, success, server failure, and retry;
- mobile software-keyboard behavior;
- final visual direction, tokens, icons, density, and motion.

Issues may be created for prerequisite discovery or backend-contract verification, but not for a final UI whose interaction has not been approved.

## Prototype verification map

| Prototype | Deterministic evidence |
| --- | --- |
| 10 | approved global mobile navigation and modal-layer behavior |
| 13 | `MOBILE_EDIT_INTEGRATED_CHECKS_PASS` |
| 14 | `MOBILE_EDIT_REFINEMENT_CHECKS_PASS` |
| 15 | `MOBILE_BASICS_SELECTION_CONTROLS_CHECKS_PASS` |
| 16 | `MOBILE_EDIT_VALIDATION_AND_GUARD_CHECKS_PASS` |
| 17 | `DESKTOP_EDIT_CORE_CHECKS_PASS` |

The corresponding scripts live beside each prototype. Screenshots are under `screenshots/edit-mode/`; review conclusions are under `reviews/`.

## Recommended future issue-slicing workflow

After the remaining design stage is complete:

1. Re-read this file and the latest decision log.
2. Inspect current production data/actions/permissions without using its appearance as a reference.
3. Build a dependency map across shared shell, data contracts, state management, surfaces, and tests.
4. Separate discovery/schema/API prerequisites from frontend behavior issues.
5. Give each issue one user-visible outcome and explicit non-goals.
6. Link the exact approved prototype state and decision clauses.
7. Include responsive, accessibility, failure, and state-preservation acceptance criteria.
8. Mark unresolved visual tokens as blocked until the visual direction is approved.
9. Order issues so shared primitives and contracts land before dependent screens.

## Ready-for-agent issue packet

When a design domain reaches `Ready`, its GitHub issue should contain this minimum packet:

- **Outcome:** one user-visible capability and the applicable desktop/mobile surfaces.
- **Approved evidence:** exact decision clauses, prototype state, screenshot, and review file.
- **Functional contract:** data, actions, permissions, draft boundary, state transitions, and persistence owner.
- **Acceptance matrix:** normal, sparse, dense, flagged/error, loading/failure, responsive, keyboard, and screen-reader behavior as applicable.
- **State preservation:** mode, draft, active section, scroll, focus restoration, and auxiliary-layer behavior.
- **Non-goals:** every nearby unfinished or separately owned design domain.
- **Prerequisites:** schema/API discovery, shared primitives, or backend mutations that must land first.
- **Verification:** deterministic unit/component/E2E cases and target viewports derived from the approved prototype rather than its implementation code.

Do not attach `.superpowers` paths to implementation issues. Only permanent tracked files under `design/` are valid UI/UX handoff evidence.

## Current next design step

Complete Recipe Edit in this order:

1. Instructions;
2. Cooking notes;
3. Estimated nutrition;
4. save request states and keyboard behavior;
5. Manage Media;
6. Organize Recipe;
7. visual-direction comparison and representative responsive validation.

Prototypes 16 and 17 remain the fixed mobile and desktop validation/dirty-guard baselines while these sections are added.
