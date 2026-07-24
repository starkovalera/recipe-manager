# Recipe Detail Prototype — Responsive and Long-Content Review

Status: Proposed for user approval  
Reviewed: 2026-07-22

## Viewports and captures

- `1440 × 900`: normal, dense/flagged, Cooking Focus drawer.
- `1024 × 768`: Import Info split view and Cooking Focus drawer.
- `390 × 844`: normal, dense/flagged, Cooking Focus media sheet.
- Full page: 48 ingredients, 38 long steps, long cooking notes, long title, no cover.

All captures are in `design/recipe-detail/screenshots/01-structure-validation/`.

## Passed findings

- Automated checks found no horizontal overflow at 390 px in dense Default View or the media sheet.
- Long title and no-cover states preserve source/time/servings and all primary actions.
- Fifty Tags and twenty Collections remain bounded to two visible names and `+N`.
- Forty-eight ingredients and thirty-eight stable numbered steps remain continuous and navigable without pagination or card repetition.
- Desktop Default View preserves fixed-width Ingredients and wider Instructions.
- Mobile Default View intentionally stacks identity, actions, status, secondary metadata, Ingredients, Nutrition, Instructions, and Notes.
- Mobile Cooking Focus uses task tabs instead of compressed desktop columns.
- Mobile media uses a bottom sheet with explicit Close and Expand controls.
- Desktop media reallocates width and keeps both cooking columns visible.

## Breakpoint risks

- At 1024 px, the drawer leaves approximately tablet-sized space for two active cooking columns. Text remains usable but wraps aggressively. Recommendation: do not approve the current 1024px drawer behavior as final without comparing it to a tablet sheet or another context-preserving option.
- The 390px dense header is stable and starts Ingredients within the first viewport, but little room remains for further metadata. Additional classifications must stay outside Default View or behind organization disclosure.
- Full long content is intentionally continuous; a later visual pass should evaluate optional within-page navigation or sticky progress only if it materially improves scanning.
- The current prototype preserves state but does not measure exact scroll-position restoration after real route transitions.

## Responsive verdict

Desktop and mobile foundations are viable. The only structural responsive decision still requiring a focused comparison is Cooking Focus media presentation around the 1024px tablet breakpoint.
