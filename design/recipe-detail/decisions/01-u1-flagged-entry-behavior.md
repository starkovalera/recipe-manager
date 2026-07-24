# U1 Decision — Entry Behavior With Unresolved Import Flags

Status: Approved  
Decision date: 2026-07-22

## Decision

Approve **Variant B: Default Recipe View with a concise status**.

When a user opens an imported recipe with unresolved review flags, the product opens the ordinary Default Recipe View. A concise status before recipe content explains that imported details need review and links clearly to Import Info.

## Required behavior

- Do not redirect the user to Import Info on entry.
- Keep the persistent `Import info` action neutral and do not add a warning icon.
- Keep detailed flags, evidence, provenance, lifecycle controls, and eligible debug information in Import Info.
- Place the concise status before uncertain recipe content in visual, keyboard, and screen-reader order.
- Returning from Import Info restores the same Default View position.
- Imported recipes without unresolved flags open the ordinary Default Recipe View without a status or warning.
- Manual recipes do not expose Import Info.

## Rationale

Variant B preserves the predictable behavior of opening a saved recipe while keeping unresolved import review visible and actionable. It does not treat every unresolved flag as a gate before the recipe can be read or used.

## Rejected alternative

Variant A opened Import Info first. It made the review task unmistakable but changed the expected destination and could interrupt use of an otherwise usable recipe.

## Evidence and artifact

- Comparison: `design/recipe-detail/wireframes/01-flagged-entry-behavior-comparison.svg`
- Rationale and critique: `design/recipe-detail/wireframes/01-flagged-entry-behavior-comparison.md`
- Research: `design/recipe-detail/research/pattern-research.md`

## Remaining decision

U2 still requires a controlled low-fidelity comparison of Difficulty and Personal rating placement. That comparison must preserve this U1 decision and all other approved Recipe Detail structure.
