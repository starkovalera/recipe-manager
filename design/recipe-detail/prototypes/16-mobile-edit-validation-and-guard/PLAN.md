# Mobile Edit Validation and Guard Prototype Plan

**Goal:** Evaluate the approved inline Save-error summary and the now-approved mobile unsaved-changes guard within the approved mobile Recipe Edit shell.

**Scope:** Isolated design prototype, screenshots, tests, review notes, and mobile decision documentation only. Do not modify production code or earlier prototypes.

## Preserved baseline

- Preserve Prototype 15 Variant A: Source selection sheet, direct Difficulty segments, centered five-star Personal rating, and 44px touch targets.
- Preserve the compact `Back / title / Save / Overflow` header, global mobile navigation, single-open accordion, compact ingredient rows, and single-item ingredient editor sheet.
- Cooking time label becomes `Cooking time (min)` and its editable value contains only the number.
- Cooking time and Servings accept positive whole numbers or empty values.
- Quantity accepts an empty value or numeric expressions such as `2`, `1.5`, `1,5`, `1/2`, `½`, and `1–2`; reject letters, emoji, and unrelated symbols.

## Scenario 1 — Basics validation after Save

- Save remains available while the draft contains errors.
- After Save fails validation, place a focused inline error summary at the beginning of the editor scroll area, above the accordion sections.
- Summary title: `5 issues need attention` for the dense demonstration state.
- Group summary links by section and use the same concise copy as the corresponding inline error.
- Selecting an error expands its section, scrolls the field into view, and moves focus to it.
- The Basics accordion header exposes a non-color-only error count.
- Demonstrate: missing Recipe title, overlong Author, invalid Cooking time, and invalid Servings.
- Required errors appear after blur or Save. Overlength and impossible numeric characters appear immediately; plausible incomplete numeric expressions wait until blur or Save.
- Never clear the user's value.

## Scenario 2 — Ingredients validation and capacity

- Demonstrate an Ingredients section-level limit error at `52 of 50 ingredients`: `Remove 2 ingredients before saving.`
- The section header exposes its error count and the Save summary links to the section.
- At exactly 50 ingredients, disable `Add ingredient` and show: `Ingredient limit reached. Remove one to add another.`
- Demonstrate an ingredient editor sheet with an empty required Ingredient name and an invalid Quantity.
- `Done` validates the ingredient sub-draft and keeps the sheet open when invalid.
- Inline copy: `Enter an ingredient name.` and `Enter a quantity using numbers, fractions, or a range.`
- Unit selection remains unchanged and valid.

## Scenario 3 — Unsaved-changes guard

- Mobile presentation is a blocking bottom sheet titled `Unsaved changes`.
- Message: `Save changes before leaving this recipe?`
- Stacked actions: `Save changes`, `Discard changes`, `Keep editing`.
- `Discard changes` is the only destructive-styled action.
- `Keep editing`, cross, system Back/Escape, backdrop, and downward swipe safely dismiss the guard and retain the draft.
- `Save changes` validates the whole draft. In the invalid demonstration state, close the guard, cancel navigation, show the inline summary, and focus it.
- Trigger examples remain Back, View/Focus, global navigation, and Manage Media. Media and Import Info auxiliary panels do not trigger it.
- Approval result: the user approved this guard treatment on 2026-08-13.

## Evidence and verification

- Create an interactive Prototype 16 with scenario controls for Basics errors, Ingredients errors, and Guard.
- Capture separate 390 × 844 screenshots for all three states, plus an ingredient-sheet error state if it materially improves evaluation.
- Test at 360, 390, and 430 CSS px: no overflow, summary focus and links, accordion error markers, inline error association, numeric rules, ingredient capacity, ingredient-sheet blocking validation, guard actions/dismissal, and 44px targets.
- Run mojibake scan, expected-path checks, and `git diff --check`.
- Do not create commits or modify Git refs.
