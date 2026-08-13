# Mobile Edit Header Comparison

Status: historical comparison; option C was approved and carried forward.

## Task

Compare two initial states for the approved mobile Recipe Detail shell while adapting Recipe Edit:

- **A:** the upper Recipe section starts expanded and becomes compact after scrolling;
- **C:** the upper Recipe section uses the compact scrolled state from entry and remains compact.

## Kept identical

- Recipe Edit stays inside the Recipes destination;
- the comparison originally kept fixed `Cancel` and `Save changes` actions above global navigation; Prototype 12 later rejected that action bar;
- global navigation remains `Recipes / Collections / Add / Notifications / Profile`;
- the single-open accordion editing model remains unchanged;
- mobile Ingredients originally retained reorder handles; Prototype 14 later removed mobile reordering;
- Media and Overflow remain in the shared compact Recipe Detail header.

## Deliberate difference

In A, editable Basics occupies the expanded middle layer and the `View / Focus / Edit` row remains visible until scroll. In C, Basics is a normal accordion section and mode switching is reached through Overflow, matching the approved compact-header behavior.

## Evaluation focus

- whether A leaves enough useful editing space at entry;
- whether C hides too much Recipe identity and mode context;
- whether the fixed Edit action bar plus global navigation is tolerable at 390 x 844;
- whether either option should proceed to an interactive prototype.

## Evidence

- `../../screenshots/edit-mode/11-mobile-edit-header-a-c-comparison-v1.png`
- `../../screenshots/edit-mode/11a-mobile-edit-header-expanded-v1.png`
- `../../screenshots/edit-mode/11c-mobile-edit-header-always-compact-v1.png`

## Decision result

Option C is the approved foundation: Recipe Edit uses the compact header from entry and Basics remains an accordion section. Prototype 12 supersedes this comparison for Save placement, and Prototype 14 supersedes its mobile ingredient-reordering detail.
