# Recipe Detail Decisions Log

Consolidated approved design artifact: `design/recipe-detail/decisions/06-approved-ux-foundation.md`.

## Approved

- Recipe Detail is split into distinct contexts.
- Default Recipe View is a reading and usage screen.
- Desktop Default View uses a compact header and two-column content foundation.
- Ingredients are in a fixed-width left column.
- Instructions are in a wider right column.
- Estimated Nutrition is below Ingredients.
- Cooking Notes are below Instructions.
- Cover is recognizable but not a hero.
- Recipe title is the strongest header element.
- Source and author have no visible `Source` / `Author` labels in Default View.
- Source and author form one compact identity row; time and servings form a separate cooking-facts row.
- `Import info` is a neutral action available for every imported recipe.
- The neutral `Import info` action has no warning icon.
- Manual recipes do not need an Import Info entry point.
- Without review flags, Default Recipe View opens normally and shows no warning.
- Import Info is a drawer or mobile bottom sheet over the current recipe context.
- Import Info contains general review flags, imported-resource groups, resource statuses, removal controls, and eligible debug data.
- Import Info does not show an extracted-recipe duplicate, `Provenance`, or `Original source`.
- Detailed import information never remains permanently visible in Default View.
- Tags and Collections are in the upper-right metadata area.
- Large Tags and Collections sets collapse to a fixed visible length with `+N`.
- Editing content and organizing metadata are separate.
- Cover Picker and Import Info are separate.
- Cooking Focus hides organization, provenance, and administrative information.
- Cooking media is optional and closed by default.
- Image generation is not the primary design method.
- Existing production UI is not a visual reference.
- With unresolved review flags, Default Recipe View opens with a concise status linking to Import Info.
- Detailed review flags remain in Import Info; returning restores the Default View position.
- Difficulty and Personal rating lead the upper-right secondary metadata group.
- The approved secondary metadata order is Difficulty / Personal rating, Collections, then Tags.
- The review status in Default View is compact and proportional to its text rather than a full-width banner.
- Long Default View content is bounded initially: Ingredients after 12 items, Instructions after 8 steps, and Notes after 4 lines; each section can be expanded and collapsed independently.
- View, Focus, and Edit remain directly reachable from every recipe context; Import Info is also reachable from Focus for imported recipes.
- Cooking Focus currently has no ingredient or instruction checkboxes and no portion multiplier.
- Import review flags are general messages, not field-level conflicts. They have one bulk `Mark all reviewed` action and no per-flag resolution controls.
- Marking all flags reviewed changes review state only; it does not alter recipe content or imported resources.
- Removed resources cannot be restored from Import Info. A compact removed-type summary may be shown without a Restore action.
- Removing a primary resource also removes its derived resources, except a derived resource currently used as the cover. Confirmation reports affected counts/types and the cover exception.
- Wide desktop Import Info reflows the recipe context; at approximately 1024 px it overlays without narrowing the page; on mobile it becomes a bottom sheet.
- Imported resources are grouped beneath their primary resource; this parent/derived hierarchy is approved.
- Image resources need recognizable thumbnails. A thumbnail may expand a larger preview inline without opening another drawer.
- Recipe Detail has one auxiliary-panel slot. Media and Import Info replace each other rather than stacking when another main-page action is used on wide desktop.
- Switching away from Import Info cancels any unconfirmed destructive action.
- Corrected B is approved: the horizontal main-action row sits below the header and starts at the cover edge.
- Main actions use two semantic groups: `View / Focus / Edit`, then `Media / Import info / Overflow`.
- Media is directly available in Default View, Cooking Focus, and Edit whenever media exists. It is hidden rather than disabled when no media exists.
- Preview and panel close controls use a cross icon. Every resource-removal entry point, including primary resources, uses the same trash icon; the cascade confirmation retains explicit text actions.
- Cascade confirmation explicitly states that the saved recipe content will not change and only imported files/links will be removed.
- Media and Import Info use the same drawer/sheet width at every breakpoint.
- Media has no Compact/Expand width control.
- Media and Import Info contain no internal navigation to one another. Users open them from the main page action row.
- Media includes imported images plus understandable external video/link actions; it does not show raw URLs as primary actions.
- At 1360 px and wider the auxiliary drawer is nonmodal and reflows the recipe context. On narrower desktop it overlays an inert unchanged page so the main menu and reading columns are not compressed.
- On mobile the auxiliary panel is a bottom sheet with both a cross and downward-swipe dismissal; content scrolling takes precedence until the sheet is at its top.
- Import Info conditionally includes an `Ignored resources` section. Ignored derived resources remain grouped by their primary source and image resources retain previews.
- Removing any secondary resource requires an inline confirmation inside its row. The confirmation states that the resource cannot be restored and that the saved recipe will not change; cancellation and Escape restore the row without removing anything.
- `Delete recipe…` is the final separated destructive item in the main-row overflow menu. It is reachable from View, Focus, and Edit, but does not appear inside Media or Import Info.
- Recipe deletion is irreversible and has no Undo. A blocking confirmation names the recipe and explains that imported files, images, and links are also deleted when present; it does not require typing the title.
- Desktop uses a centered confirmation dialog. Mobile uses a bottom sheet with a cross and Cancel, but no swipe dismissal for this destructive decision.
- Successful deletion returns to the Recipes list and announces `Recipe deleted`. A failed request keeps the confirmation open and shows `Recipe couldn’t be deleted. Try again.`

## Resolved comparisons

### Behavior when unresolved review flags exist

Approved: open Default View with a concise status linking to Import Info. Do not redirect to Import Info on entry.

### Difficulty and rating placement

Approved: keep Difficulty and Personal rating in the upper-right secondary metadata area, above Collections and Tags.

### Primary action placement

Approved: corrected B. Retain A only as historical comparison evidence; do not continue both variants in subsequent prototypes.

## Not in current scope

- global application navigation redesign;
- production implementation;
- final design system;
- actual cooking-session nutrition;
- persistent cooking sessions;
- step-level media mapping.
