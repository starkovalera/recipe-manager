# Prototype 16 review — Mobile Edit validation and guard

Status: approved. Save summary and mobile guard behavior were approved on 2026-08-13.

## Task and preserved decisions

Evaluate errors for Basics and Ingredients after global Save, plus a safe mobile exit for a dirty Recipe Edit draft. The compact mobile Edit toolbar, global navigation, one-open accordion, and Prototype 15 Variant A controls remain unchanged. Prototype-only mock data is used; no production code is in scope.

## UX critique

The error summary stays above the editor accordions, reports the full correction workload, and links directly to inputs or the affected section. This retains local field context while making hidden section errors discoverable. Ingredient-sheet errors remain inside the local sheet because `Done` validates its sub-draft rather than the whole recipe. The `52 of 50` constraint is presented at section level and disables adding.

The guard has an explicit safe exit: `Keep editing` is visually neutral, Close/backdrop/Escape/swipe preserve the draft, and only `Discard changes` is destructive. `Save changes` does not proceed with invalid input; it returns the user to the focused summary.

## Visual critique

The error treatment uses icon, border, text, and count rather than red alone. The summary is intentionally compact so it does not become a second permanent header. The destructive guard action is separated from the primary Save path without making every action look like a destructive button.

## Product-fit critique

One recipe-level Save retains cross-section validation. The 50-item capacity guard is visible before an impossible add action. The prototype intentionally does not define maximum lengths for title, author, or ingredient name; it only demonstrates their approved error language.

## Accessibility and responsive critique

All interactive controls tested are at least 44 px; the summary is focusable after failed Save, its links focus the related field, and fields use `aria-invalid` plus associated error text. Modal sheets use `role=dialog`, make the editor inert, restore trigger focus on safe dismissal, and support Escape/backdrop/swipe dismissal. Automated browser checks ran at 360, 390, and 430 CSS px with no horizontal overflow.

## Evidence and visual follow-up

- `../../screenshots/edit-mode/16a-mobile-edit-basics-errors-v1.png`
- `../../screenshots/edit-mode/16b-mobile-edit-ingredients-errors-v1.png`
- `../../screenshots/edit-mode/16c-mobile-edit-unsaved-guard-v1.png`
- `../../screenshots/edit-mode/16d-mobile-edit-ingredient-errors-v1.png`

Design concern: the summary plus a collapsed section can make the first invalid Basics field fall below the fold at 360 px. The interaction is approved and mitigated by focused summary links; final density must be rechecked during visual execution and localized-label stress testing.
