# Integrated Mobile Recipe Edit Baseline Review

Status: approved integrated baseline; later refinements supersede ingredient reordering and guard details

## Task and state

The prototype combines the approved mobile shell with the approved accordion and ingredient-editor interactions. It is a reusable baseline for designing the remaining Edit Mode sections rather than a final visual design.

## Preserved decisions

- always-compact mobile Recipe Edit header;
- `Back / truncated title / Save / Overflow`;
- Media and Import Info in Overflow;
- one modal sheet slot covering global navigation;
- single-open section accordion;
- compact ingredient summaries, trash actions, and one-item editor sheet; Prototype 14 later removes mobile reorder handles;
- unchanged global navigation within Recipes.

## UX critique

- The top Save action restores substantially more editing height than either rejected bottom action bar.
- Five collapsed section headers remain legible and permit direct Ingredients-to-Instructions switching without a separate navigation sheet.
- The direct Media shortcut is less discoverable in Edit, but Save is correctly prioritized for the active task.
- The provisional Notes and Nutrition forms must not be treated as approved; each needs a dedicated next iteration.
- The dirty guard in this historical baseline demonstrated the state boundary only. Prototype 16 later approved its actions, copy, dismissal, and validation behavior.

## Visual and responsive critique

- At 390 x 844, four ingredient rows, Add ingredient, and the neighboring section labels remain visible together.
- At 360 px, the title truncates before Save or Overflow compresses.
- The global Add action remains visually prominent, but no longer competes with a second bottom editing toolbar.
- Long ingredient summaries truncate to one line by design; the full summary remains the editor-entry button and must have an accessible full name in production.

## Accessibility review

- Icon controls have accessible names and 44 CSS-pixel targets.
- Sheets make the editor inert, receive focus, trap keyboard focus, support Escape, and restore focus to their triggers.
- Nonblocking sheets retain explicit Close and swipe-down dismissal. The dirty guard does not swipe-dismiss.
- Form controls use visible labels; the prototype has visible `:focus-visible` treatment.

## Product-fit review

- Recipe content stays in one draft while import-resource actions remain outside that draft.
- Media and Import Info placeholders demonstrate context preservation without prematurely redesigning those approved panels.
- The baseline is sufficiently stable to continue with one Edit section at a time.

## Next unresolved section work

1. Instructions row editing and the mobile single-step editor.
2. Cooking notes field behavior and long-text affordances.
3. Estimated nutrition structure, partial values, units, and validation.
4. Basics field validation and mobile keyboard behavior.
