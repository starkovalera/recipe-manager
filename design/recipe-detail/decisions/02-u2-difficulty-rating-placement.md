# U2 Decision — Difficulty and Personal Rating Placement

Status: Approved  
Decision date: 2026-07-22

## Decision

Approve **B2** for the Default Recipe View header.

Difficulty and Personal rating remain in the upper-right secondary metadata area. They form the first compact row, followed by Collections and Tags:

```text
Difficulty · Personal rating
Collections
Tags
```

## Required behavior

- Keep Difficulty and Personal rating outside the primary title, inline source/author/time/servings, and action region.
- Keep the three rows in one bounded secondary metadata group.
- Keep Difficulty and Personal rating visually restrained so they do not compete with recipe identity or primary actions.
- Show complete visible Collection and Tag names with fixed `+N` disclosure.
- Preserve the same semantic and DOM order on mobile.
- Do not encode Difficulty only through color.
- Give Personal rating an accessible numeric value, such as `4.5 out of 5`, even if stars are later added visually.
- Route editing to Organize Recipe; Default View remains read-oriented.

## Rationale

B2 makes Difficulty easier to find during a cook/no-cook judgment without promoting it or Personal rating into the primary identity region. Placing the short, stable row before variable-density Collections and Tags also creates a more efficient mobile scan order.

## Rejected alternatives

- **Alternative A:** placing Difficulty and Personal rating near primary recipe metadata created too much competition in the strongest header region.
- **B1:** placing Collections and Tags first kept a conventional category-first structure but made Difficulty easier to overlook beneath two dense disclosure rows.

## Evidence and artifacts

- Initial placement comparison: `design/recipe-detail/wireframes/02-difficulty-rating-placement-comparison.md`
- Order refinement: `design/recipe-detail/wireframes/03-secondary-metadata-order-comparison.md`
- Research: `design/recipe-detail/research/pattern-research.md`

## Remaining scope

U1 and U2 are now resolved. No structural Recipe Detail decisions from the approved current scope remain open. Prototype and high-fidelity work still require explicit approval.
