# Recipe Detail UX Overview

Updated: 2026-08-13

This file is a navigation map, not an independent requirements source. It intentionally avoids repeating detailed behavior from the decision records.

## Context model

```text
Recipe
├── Default Recipe View
├── Cooking Focus
│   └── Optional Media
├── Import Info
├── Edit Recipe Content
├── Manage Media and Cover
└── Organize Recipe
```

These contexts separate reading, focused use, import review, content editing, media management, and organization rather than combining them into one overloaded page.

## Source-of-truth map

| Need | Read |
| --- | --- |
| Current boundary, completed work, and next gate | [`decisions/current-scope.md`](decisions/current-scope.md) |
| Default View, Focus, Media, Import Info, responsive panels, and deletion | [`decisions/06-approved-ux-foundation.md`](decisions/06-approved-ux-foundation.md) |
| Current Recipe Edit contract and unresolved sections | [`decisions/07-edit-mode-current-decisions.md`](decisions/07-edit-mode-current-decisions.md) |
| Auxiliary panels and Manage Media entry behavior | [`decisions/09-edit-mode-auxiliary-context-behavior.md`](decisions/09-edit-mode-auxiliary-context-behavior.md) |
| Product-wide mobile shell | [`decisions/11-global-mobile-shell.md`](decisions/11-global-mobile-shell.md) |
| Mobile Edit shell and Save placement | [`decisions/12-mobile-edit-shell-and-save-action.md`](decisions/12-mobile-edit-shell-and-save-action.md) |
| Desktop Basics, Ingredients, validation, and guard | [`decisions/13-desktop-edit-basics-validation-and-entry-behavior.md`](decisions/13-desktop-edit-basics-validation-and-entry-behavior.md) |
| Chronological approvals and supersessions | [`decisions/decision-log.md`](decisions/decision-log.md) |
| Implementation readiness and evidence | [`implementation-handoff.md`](implementation-handoff.md) |

## Reading rule

Start with `current-scope.md`, then read only the decision record for the surface being designed or implemented. Use the decision log for history and supersessions. Prototypes and screenshots demonstrate approved behavior but do not replace the written contract.
