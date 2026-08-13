# Mobile Basics Selection Controls Comparison Plan

**Goal:** Compare two touch-oriented replacements for the mobile Basics dropdowns without changing Prototype 14 or recording a final decision.

**Scope:** Isolated design prototype and screenshots only. No production code, APIs, schemas, tests, or production CSS.

## Shared baseline

- Preserve the compact Recipe Edit header, global mobile navigation, seven Basics fields, and equal Source/Author plus Cooking time/Servings rows from Prototype 14.
- Use the same realistic values in both variants: Instagram, Moderate, 4 out of 5.
- Use touch targets of at least 44 CSS px and visible keyboard focus.
- Keep Prototype 14 unchanged.

## Variant A — Hybrid controls (recommended)

- Source is a field-like button that opens a mobile bottom sheet containing Manual, Instagram, Threads, TikTok, and Other as full-width rows with the current value checked.
- Difficulty spans the full content width and exposes Easy, Moderate, and Hard as a three-option segmented control. No selected option represents Not set; include a visible Clear action only when a value is selected.
- Personal rating spans the full content width and exposes five star buttons. Preserve an accessible numeric value such as `4 out of 5`; include a visible Clear action only when rated.

## Variant B — Consistent selection sheets

- Source, Difficulty, and Personal rating remain field-like buttons in the equal two-column form grid where applicable.
- Each opens the same bottom-sheet selection pattern with full-width rows and a checkmark.
- Difficulty options are Not set, Easy, Moderate, Hard.
- Rating options are Not rated and whole values 1 through 5 out of 5.

## Evidence and verification

- Create an interactive comparison under `design/recipe-detail/prototypes/15-mobile-basics-selection-controls/`.
- Capture separate 390 × 844 screenshots for Variant A and Variant B plus one comparison image if useful.
- Test both variants at 360, 390, and 430 CSS px for overflow, target sizes, accessible names, option counts, and bottom-sheet dismissal.
- Document trade-offs and leave the selection explicitly unresolved.
- Do not modify Git refs or create commits.
