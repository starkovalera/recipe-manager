# Mobile Recipe Edit: Basics selection controls

Status: Variant A selected; star-rating alignment refined in v2.

This isolated Prototype 15 compares two replacements for the fixed mobile Basics selects from Prototype 14. It preserves the compact Back / title / Save / Overflow editor toolbar, the navigation-only global mobile bar, the Basics accordion context, and seven realistic Basics fields.

## Variants

### A — Hybrid controls (recommended)

- Source is a field-like button that opens a checked bottom-sheet list: Manual, Instagram, Threads, TikTok, Other.
- Difficulty exposes Easy, Moderate, and Hard directly. No selected segment means Not set. A visible Clear action appears only when selected.
- Personal rating exposes five 44 px star buttons. Its accessible value remains numeric (4 out of 5); Clear appears only when rated.

### B — Consistent selection sheets

- Source, Difficulty, and Personal rating use field-like controls in the equal two-column Basics grid.
- Each opens the same checked-row bottom-sheet pattern.
- Difficulty includes Not set; rating includes Not rated and 1–5 out of 5.

## Interaction and accessibility checks

- All actionable controls are at least 44 CSS px tall or wide.
- Controls have visible keyboard focus, accessible labels, selected states, Escape dismissal, backdrop/Close dismissal, and a downward swipe dismissal on the sheet handle.
- The background editor becomes inert while a sheet is open; closing returns focus to its triggering control.
- The browser test checks both variants at 360, 390, and 430 CSS px for horizontal overflow, option counts, accessible names, targets, and dismissal.

## Selection result and trade-off

Variant A is the selected direction. It reduces interaction cost for the two smallest sets while preserving a sheet for Source. The five-star group is centered within the full-width rating area; Clear remains a separate right-aligned action in the heading. Variant B remains available as comparison evidence.

## Evidence

- ../../screenshots/edit-mode/15a-mobile-basics-hybrid-v1.png
- ../../screenshots/edit-mode/15a-mobile-basics-hybrid-v2.png
- ../../screenshots/edit-mode/15b-mobile-basics-sheets-v1.png
- ../../screenshots/edit-mode/15c-mobile-basics-source-sheet-v1.png

Open index.html directly, or run test_prototype.js and capture_screenshots.js with the bundled Node and Playwright runtime.
