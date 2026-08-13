# Mobile Recipe Edit: validation and unsaved-changes guard

Status: approved low-fidelity behavior foundation.

Approved: 2026-08-13

This isolated Prototype 16 preserves Prototype 15 Variant A: the compact `Back / title / Save / Overflow` toolbar, global navigation, one-open-section accordion, checked Source sheet entry point, direct Difficulty selection, centered five-star rating, and 44 px touch targets.

## States

- **Basics errors** shows the inline `5 issues need attention` summary above the accordion, the four Basics field errors, and a non-color-only `4 errors` section marker. Summary links expand Basics and focus their input.
- **Ingredients errors** shows `52 of 50 ingredients`, the required removal message, a disabled Add ingredient action, and an ingredient section error count. The ingredient editor's `Done` validates its local draft without closing the sheet.
- **Unsaved-changes guard** is an approved blocking mobile bottom sheet. `Save changes` validates the recipe-level draft and returns focus to the summary when invalid. `Discard changes` is the only destructive action; Close, Escape, backdrop, swipe, and `Keep editing` retain the draft.

## Input rules shown

`Cooking time (min)` and Servings allow an empty value or positive whole minutes/numbers. Quantity allows an empty value or numeric expressions including `2`, `1.5`, `1,5`, `1/2`, `½`, and `1–2`; letters, emoji, and unrelated symbols are invalid. Invalid numeric characters and overlength feedback appear immediately; missing required values appear on blur or Save in the production pattern.

## Run locally

Use the bundled Node runtime with `NODE_PATH` set to its node_modules directory, then run `test_prototype.js` or `capture_screenshots.js`. The tests cover 360, 390, and 430 CSS px widths, overflow, targets, error summary focus, section error cues, quantity/capacity messaging, ingredient-sheet validation, and guard outcomes.

## Approval result

The inline Save error summary, validation hierarchy, and mobile bottom-sheet guard are approved. The summary-density concern at 360 px remains a visual-execution check, not an unresolved interaction decision.
