# Temporary Artifact Consolidation Map

Status: complete for the currently approved Recipe Detail and partial Recipe Edit scope
Date: 2026-08-13

## Purpose

This map records where approved working-session evidence from untracked `.superpowers` directories now lives permanently. Future design and implementation agents must use the permanent artifacts, not temporary session output.

## Consolidated material

| Temporary working theme | Permanent source of truth |
| --- | --- |
| Desktop Basics layout alternatives and approved two-zone option A | `13-desktop-edit-basics-validation-and-entry-behavior.md`, Prototype 17 normal state |
| Desktop Difficulty and Personal rating controls | Decision 13, Prototype 17 normal state |
| Desktop full-page Edit, sticky rail, global Save model | Decision 13, Prototype 17 normal state |
| Desktop validation hierarchy and unsaved guard | Decision 13, Prototype 17 validation/guard states, review 17 |
| Mobile Recipe Detail header alternatives and rejected cover experiments | `08-mobile-recipe-detail-prototype-spec.md`, `11-global-mobile-shell.md`, Prototypes 06 and 10 |
| Mobile global navigation and modal-layer behavior | `10-mobile-global-navigation.md`, `11-global-mobile-shell.md`, Prototype 10 |
| Early Edit layout, auxiliary-panel, Unit, Manage Media, and mobile Ingredient comparisons | `07-edit-mode-current-decisions.md`, `09-edit-mode-auxiliary-context-behavior.md`, gallery history, permanent screenshots under `screenshots/edit-mode/` |
| Approved mobile Edit shell, Basics, Ingredients, validation, and guard | Decisions 07 and 12, Prototypes 13–16 and review 16 |

## Intentionally not promoted as requirements

- rejected comparison variants;
- obsolete mobile section-index and ingredient-reorder concepts;
- obsolete Manage Media-inside-Media-panel concept;
- waiting screens that only indicated a pending decision;
- session server metadata, PIDs, verification scratch files, and orchestration reports;
- styling visible in temporary companions beyond the explicitly approved low-fidelity structure.

## Handoff rule

Implementation issues may link only to tracked permanent files under `design/`. If a future agent finds a decision represented only under `.superpowers`, that decision is not ready for implementation issue slicing until it is promoted through the normal decision/prototype/review process.
