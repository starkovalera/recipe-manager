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

- Edit Mode is one page with wide sections and explicit global `Save changes` / `Cancel` actions.
- Desktop Edit Mode uses a persistent left section rail; mobile uses a compact current-section index that opens a navigational bottom sheet.
- Ingredient notes are not shown or edited. Editing inputs use content-based maximum widths instead of stretching across the full canvas.
- Edit Mode preserves unsaved recipe edits, active section, and scroll position when Media or Import Info opens, closes, or replaces the other auxiliary panel.
- In Edit Mode, Media becomes Manage Media with a separate media draft, capacity, upload, cover selection, image removal, and read-only external media links. View and Focus Media remain read-only.
- Ingredient Unit uses a fixed localized dictionary. The approved corrected-A interaction expands the active ingredient row with autocomplete search and a bounded chip list followed by `+N`.
- On mobile, the expanded Unit selector spans the full editor width beneath the ingredient row; it is not indented beneath Quantity and Unit.
- Mobile Ingredients uses a compact one-line list rather than three persistent inputs per ingredient.
- Every mobile ingredient row keeps a reorder handle, summary, and the standard trash action.
- The approved editor entry is option A: the full summary area is a button with a chevron. Activating it opens a bottom sheet for one ingredient.
- The ingredient sheet edits Ingredient, Quantity, and Unit; `Done` applies its sub-draft to the Recipe Edit draft, while only global `Save changes` persists the recipe.
- `Add ingredient` opens the same sheet empty. Dismissing a changed ingredient sub-draft requires a discard decision.
- Ingredient reordering supports direct drag plus accessible move commands.

### Edit Mode auxiliary contexts — 2026-07-24

- The earlier decision that Media becomes Manage Media inside Edit Mode is superseded.
- Media is now the same read-only auxiliary panel in View, Focus, and Edit. Import Info is also an auxiliary panel over Edit Mode.
- Opening, replacing, or closing Media or Import Info does not leave Edit Mode and does not trigger a navigation guard; the unsaved Recipe Edit draft, active section, and scroll position are preserved.
- `Manage media` opens from the Media panel as a separate full-screen editing workspace on mobile and desktop with its own draft and `Save media changes` / `Cancel`.
- Entering Manage Media from a dirty Recipe Edit draft leaves Edit Mode and requires a navigation guard. The guard must not silently discard recipe changes; its exact actions and copy remain unresolved.
- Import resource removal is immediate after the existing inline confirmation and is independent of global Recipe Edit `Save changes`.
- Immediate resource removal does not modify either the saved recipe or the unsaved Recipe Edit draft. Cascade counts/types and current-cover protection remain in force.
- Successful removal updates Import Info in place. Failure remains local to Import Info and leaves the Recipe Edit draft intact.

### Mobile header and import navigation — 2026-07-24

- Mobile expanded Recipe Detail uses three levels: a top utility row, the recipe identity block, then the `View / Focus / Edit` mode row.
- The expanded top row contains Back on the left and Media plus Overflow on the right. The Media icon opens only the Media bottom sheet.
- The compact scrolled header is one row: Back, a truncated recipe title, Media, and Overflow.
- In the compact state, Overflow opens a bottom sheet whose first row contains `View / Focus / Edit`.
- On mobile, Import Info is not a tab inside Media and the two areas contain no internal switching control.
- For imported recipes, `Import info` is a separate item in the Overflow sheet, below the mode row and before Export. Manual recipes omit it.
- Mobile Import Info opens as its own dedicated bottom sheet or full-height mobile section. It is an administrative destination rather than a companion media panel over visible recipe content.
- Media remains available for manual recipes even when they have no media yet, because it provides the path to Manage Media and image upload when capacity allows. Only Import Info is conditional on the recipe being imported.
- On mobile, the unresolved-import review status spans the full Recipe Detail width. This intentionally differs from the compact proportional desktop status.
- The mobile review-status strip remains full width but uses compact vertical padding and explicit spacing before the following metadata section.
- When no review-status strip is present, Default View keeps an explicit vertical gap between the mode row and the metadata section. When review status is present, the strip's own bottom spacing provides that separation instead.
- While unresolved import flags exist, Overflow shows a notification dot and the `Import info` item repeats the same dot. Accessible names explicitly announce that import review is needed; the dots disappear after `Mark all reviewed`.
- These notification dots indicate pending review state and do not turn neutral Import Info into a warning action or add a warning icon.
- The earlier proposed combined `Recipe resources` entry and Media / Import Info switch is rejected. Desktop retains separate Media and Import Info drawer entry points and behavior.

### Mobile global navigation — 2026-07-24

- The approved mobile application bar uses four stable top-level destinations around a visually distinct central creation action: `Recipes / Collections / + / Notifications / Profile`.
- Recipes and Collections remain separate equal-priority destinations. Search belongs inside Recipes rather than in the global bar.
- The central `+` is the `Add recipe` action, not a selected destination. It opens a compact chooser for `Import recipe` and `Create manually`.
- Administration is available from Profile for eligible roles. The global bar never adds a role-dependent Admin position or changes geometry between roles.
- The global bar remains visible on ordinary application pages in View, Focus, and Edit.
- Every modal mobile sheet, including Add, Media, Overflow, Import Info, metadata disclosure, and recipe deletion, opens above and fully covers the global bar. The covered bar is hidden from interaction and accessibility navigation until the sheet closes.
- Mobile sheets use one modal-layer slot. Transitions such as Overflow to Import Info and Overflow to Delete replace the current sheet instead of stacking another dialog.
- Choosing Import or Manual Create enters a focused full-screen creation flow without the global bar. Cancel or Back owns exit and any dirty-draft protection.

### Global mobile application shell — 2026-07-24

- The approved mobile header and global navigation now form the default application shell for all future mobile screens, not only Recipe Detail.
- Root destinations such as Recipes, Collections, Notifications, and Profile do not show Back. They use an expanded title with contextual actions and a compact sticky title row after scroll.
- Nested and detail screens show icon-only Back at the left edge. Their compact sticky state contains Back, a truncated title, and only essential contextual utilities.
- Expanded nested/detail screens may place screen identity or summary below the utility row and local modes below identity. These middle layers are screen-specific rather than global navigation.
- Recipe Detail instantiates the pattern as Back / Media / Overflow, recipe identity, then `View / Focus / Edit`; its compact state is Back / truncated title / Media / Overflow.
- The fixed bottom bar remains `Recipes / Collections / Add / Notifications / Profile` on ordinary application pages. Recipe Detail remains inside the Recipes destination.
- Modal sheets use one slot and fully cover the bottom bar. Focused Import and Manual Create flows replace the ordinary shell and own exit through Back or Cancel.
- Future screen designs must identify their hierarchy level, compact-bar essentials, active global destination, and modal-layer behavior before visual styling.
- The consolidated approved contract is recorded in `design/recipe-detail/decisions/11-global-mobile-shell.md`.

## Resolved comparisons

### Behavior when unresolved review flags exist

Approved: open Default View with a concise status linking to Import Info. Do not redirect to Import Info on entry.

### Difficulty and rating placement

Approved: keep Difficulty and Personal rating in the upper-right secondary metadata area, above Collections and Tags.

### Primary action placement

Approved: corrected B. Retain A only as historical comparison evidence; do not continue both variants in subsequent prototypes.

## Not in current scope

- production implementation;
- final design system;
- actual cooking-session nutrition;
- persistent cooking sessions;
- step-level media mapping.
