# Prototype 17 review — Desktop Edit approved core

Status: approved low-fidelity behavior consolidation
Date: 2026-08-13

## UX

- Pass: one global draft and one Save/Cancel pair preserve the mental model of editing one recipe.
- Pass: the left rail supports direct section navigation while ordinary page scrolling remains available.
- Pass: the two-zone Basics layout separates identity from cooking facts and assessment without introducing cards.
- Pass: Cooking time and Servings now share the mobile rule: empty or positive whole number. Quantity remains a separate expression field.
- Pass: the failed-Save hierarchy connects overall summary, rail markers, section state, and inline recovery.
- Pass: the centered guard is appropriate for a desktop navigation-blocking decision.

## Visual and product fit

- Pass for low fidelity: content-based widths prevent numeric and segmented controls from stretching across the editor.
- Pass: Ingredients retain productivity-oriented density and the Ingredient name receives the flexible width.
- Deferred: final typography, colors, icon system, spacing, and motion require the visual-direction stage.

## Accessibility

- Pass: fields have associated labels; icon-only controls have accessible names; validation uses text and `aria-invalid`.
- Pass: the failed-Save summary is focusable and links to affected fields/sections.
- Pass: the guard is a modal dialog with explicit non-destructive and destructive actions.
- Production requirement: implement focus trapping/restoration, browser `beforeunload`/router protection, live save status, and an accessible non-drag reorder path.

## Responsive and long content

- Pass at 1440 × 900 for the approved desktop state.
- The Basics zones stack below the narrower-desktop threshold while preserving semantic grouping.
- Exact threshold, localization pressure, and maximum field lengths remain unresolved and must be stress-tested after those contracts are known.

## Scope boundary

The visible Instructions, Cooking notes, and Nutrition content demonstrates continuous-page structure only. Their editing, validation, and error recovery are not approved by Prototype 17.
