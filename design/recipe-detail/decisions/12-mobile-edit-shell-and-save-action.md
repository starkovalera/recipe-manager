# Mobile Recipe Edit Shell and Save Action

Status: approved

Approved: 2026-07-25
Updated: 2026-08-13

## Decision

Mobile Recipe Edit uses the approved compact Recipe Detail shell from entry. The upper section does not begin expanded and does not reveal a separate identity or mode block before scrolling.

The compact top toolbar is:

```text
Back | truncated recipe title | Save | Overflow
```

- `Save` is the persistent recipe-draft action.
- Media and Import Info move to Overflow while Edit is active.
- The fixed bottom `Cancel / Save changes` bar is removed.
- The global `Recipes / Collections / Add / Notifications / Profile` bar remains visible and unchanged.
- Recipe-edit actions never become global-navigation items.
- Back exits Edit. When unsaved changes exist, Back opens the dirty-draft guard rather than discarding changes.
- The approved guard is a blocking bottom sheet with `Save changes`, destructive-only `Discard changes`, and neutral `Keep editing`. Safe dismissal keeps the draft.

## Editing structure

- Basics, Ingredients, Instructions, Cooking notes, and Estimated nutrition form one single-open accordion.
- Basics is a normal accordion section; it is not duplicated in the compact header.
- The approved mobile ingredient rows and single-item ingredient sheet remain unchanged.
- Opening Media or Import Info from Overflow preserves the Recipe Edit draft, active accordion section, and scroll position.

## Rejected alternatives

- An expanded Recipe identity/Basics header at entry uses too much of the initial editing viewport.
- A fixed `Cancel / Save changes` bar above global navigation creates two competing bottom bars.
- A lightweight dirty-state accessory above global navigation is better than the original heavy bar but still reduces editing height and competes with the central Add action.
- Hiding global navigation and treating Edit as a focused full-screen flow contradicts the approved mobile shell.

## Evidence

- `../screenshots/edit-mode/11-mobile-edit-header-a-c-comparison-v1.png`
- `../screenshots/edit-mode/12-mobile-edit-save-actions-comparison-v1.png`
- `../screenshots/edit-mode/12a-mobile-edit-save-top-toolbar-v1.png`

## Still unresolved

- Save request in-progress, success, and server-failure presentation. Validation-error behavior is approved in Prototype 16.
- Behavior while the software keyboard is open.
- Detailed editing and validation for Instructions, Cooking notes, and Estimated nutrition.
