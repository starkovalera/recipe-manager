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

The mobile current-section index, mobile reorder handle, and in-Edit Manage Media statements in the preceding historical block are superseded by the later 2026-07-24 and 2026-07-25 entries below. Desktop reordering remains approved.

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

### Mobile Recipe Edit shell and Save action — 2026-07-25

- Mobile Recipe Edit uses the compact Recipe Detail header from entry; it does not begin with an expanded identity/Basics header.
- Mobile editing uses a single-open accordion. Basics is one of its sections rather than a duplicate block in the header.
- The compact Edit toolbar is Back, truncated recipe title, `Save`, and Overflow.
- `Save` replaces direct Media while Edit is active. Media and Import Info remain available from Overflow.
- The former fixed bottom `Cancel / Save changes` bar and the proposed bottom dirty-state accessory are rejected.
- Back owns exit and invokes a dirty-draft guard when unsaved changes exist.
- The global `Recipes / Collections / Add / Notifications / Profile` bar remains visible, unchanged, and navigation-only.
- The consolidated decision is recorded in `design/recipe-detail/decisions/12-mobile-edit-shell-and-save-action.md`.

### Mobile Recipe Edit Basics and Ingredients refinement — 2026-07-25

- Mobile Basics has seven fields: Recipe title; Source; Author; Cooking time; Servings; Difficulty; and Personal rating.
- Recipe title is full width. Source / Author, Cooking time / Servings, and Difficulty / Personal rating are equal two-column pairs with consistent control heights.
- Source is a five-value fixed select: Manual, Instagram, Threads, TikTok, Other.
- Difficulty is a fixed select: Not set, Easy, Moderate, Hard. Personal rating is a fixed select: Not rated and 1–5 out of 5 in whole-number steps.
- Difficulty and Personal rating persistence remain future backend work.
- Mobile ingredient rows retain only the summary-button editor and the trash action. DnD, reorder handles, reorder copy, and accessible move commands are removed on mobile.
- Desktop ingredient reordering and instruction reordering are unchanged and outside this refinement.
- Mobile Basics uses a hybrid selection pattern: Source opens a checked bottom sheet; Difficulty exposes Easy / Moderate / Hard directly; Personal rating exposes five whole-value stars.
- The rating-star group is centered in its full-width field area. `Clear` remains a separate right-aligned heading action.

### Desktop Recipe Edit Basics, Ingredients, validation, and guard — 2026-07-25

- Desktop Recipe Edit is one continuous page with a sticky left section rail, ordinary page scrolling, and scrollspy. Scrollspy updates the active rail item but never moves focus or scroll position on its own.
- The page owns one Recipe Edit draft and one global `Save changes` / `Cancel` pair. Individual sections do not save independently.
- Desktop Basics uses two semantic zones without cards: Recipe identity on the left; Cooking facts & assessment on the right.
- Recipe identity contains Title, fixed Source, and Author.
- Cooking facts & assessment contains compact Cooking time, Servings, Difficulty, and Personal rating controls; these controls use content-based widths rather than filling the zone.
- Cooking time edits only a numeric value and displays `min` as a fixed non-editable suffix. Cooking time and Servings follow the approved Quantity numeric syntax and may be empty.
- Difficulty uses visible `Easy / Moderate / Hard` segments and a separate `Clear` action for the unset state. `Not set` is not a visible segment.
- Personal rating uses five whole-value stars only: `1`, `2`, `3`, `4`, or `5`. Half-star values are unsupported. A visible `N of 5` value and separate `Clear` action remain available.
- Desktop Ingredients uses compact rows containing reorder handle, optional Quantity, fixed-dictionary Unit, required Ingredient name, and the standard trash action. Ingredient notes are not shown or edited.
- A new ingredient begins with empty Quantity and `No unit`. The 50-ingredient limit is reported as a section-level aggregate error.
- Validation is hybrid: invalid numeric syntax and overlength appear once present; required-field errors appear after blur or Save; aggregate constraints appear at section level.
- Failed Save shows a linked overall error summary, marks every affected rail section, and moves focus to the first invalid field.
- The approved centered desktop guard is `Unsaved changes` / `Save changes before leaving this recipe?` with `Save`, `Discard`, and `Cancel`.
- The guard applies to Back, browser Back, View/Focus, other navigation, and entry into Manage Media. It does not apply to Media or Import Info auxiliary panels.
- The consolidated contract is recorded in `design/recipe-detail/decisions/13-desktop-edit-basics-validation-and-entry-behavior.md`.

### Desktop Import Info entry refinement — 2026-07-25

- The earlier permanent desktop `Import info` main-row button is superseded. On desktop, Import Info is an item under recipe Overflow in View, Focus, and Edit.
- When unresolved flags exist, Overflow shows a notification dot and the `Import Info` menu item repeats the dot.
- On first entry into a flagged recipe, Import Info opens automatically. It does so only once during that recipe visit; closing it or switching View/Focus/Edit does not reopen it.
- Recipes without unresolved flags do not auto-open Import Info. Manual recipes omit the import-only item; Media remains available.
- This first-entry behavior supersedes the earlier decision to always enter flagged recipes in ordinary Default View with only a compact review status.

### Mobile Recipe Edit validation and unsaved-changes guard — 2026-08-13

- A failed mobile Save shows a focusable linked summary above the accordion sections. Links open and focus affected fields or sections, and section headers expose text error counts.
- Basics and Ingredients use hybrid validation: impossible numeric syntax and overlength appear immediately; required and plausibly incomplete values appear after blur, local `Done`, or Save.
- Ingredient-sheet errors remain inside the ingredient sub-draft. The 50-ingredient maximum is a recipe-level section error and is repeated in the failed-Save summary.
- Cooking time is labelled `Cooking time (min)` and edits only the numeric value. Cooking time and Servings accept empty or positive whole-number values; Quantity also accepts decimal, fraction, and range expressions.
- The approved mobile dirty-draft guard is a blocking bottom sheet: `Unsaved changes`, `Save changes before leaving this recipe?`, with `Save changes`, destructive-only `Discard changes`, and neutral `Keep editing`.
- Close, Escape, backdrop, downward swipe, and system Back safely dismiss the guard and retain the draft.
- The guard applies to Back, browser Back, View/Focus, global destinations including Add, and Manage Media. Media and Import Info do not invoke it because they remain auxiliary Edit contexts.
- Prototype 16 and its review are the approved low-fidelity evidence.

## Resolved comparisons

### Behavior when unresolved review flags exist

Approved and superseding the earlier comparison: on the first entry into a recipe with unresolved flags, open Import Info automatically over the recipe. Do this only once per recipe visit; after the panel is closed, View/Focus/Edit changes do not reopen it automatically.

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
