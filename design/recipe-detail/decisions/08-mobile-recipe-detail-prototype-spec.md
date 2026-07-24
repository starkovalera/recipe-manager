# Mobile Recipe Detail Prototype Specification

Status: approved concept; written specification awaiting review  
Date: 2026-07-24

## Purpose

Create a complete, isolated, mobile-first Recipe Detail prototype that brings the already approved Recipe Detail decisions into one continuous working experience.

The prototype covers reading, Cooking Focus, Media, Import Info, metadata disclosure, and rare or destructive recipe actions. Edit Mode remains visible in the approved main-action structure but is not implemented because its design is still in progress.

This is a design artifact only. It must not use production components, application APIs, routes, schemas, or styles.

## Approved direction

Use a sequential mobile reading page rather than compressing the desktop columns or introducing permanent tabs in Default View.

```text
Default View
├── compact recipe header
├── two-row main actions
├── optional compact review status
├── compact secondary metadata
├── Ingredients
├── Instructions
├── Estimated Nutrition
└── Cooking Notes
```

Default View remains a complete reading page. Ingredients and Instructions become switchable views only inside Cooking Focus, where reducing distraction is the primary task.

## Preserved decisions

- Recipe Manager is a productivity product, not a recipe blog.
- Mobile is designed intentionally rather than produced by shrinking the desktop layout.
- The cover is recognizable but never becomes a hero image.
- Recipe title remains the strongest header element.
- Source identity and cooking facts are separate rows.
- Default View does not show visible `Source` or `Author` field labels.
- Corrected-B main-action placement and the two semantic action groups remain recognizable on mobile.
- `Import info` remains neutral and contains no warning icon.
- A recipe with unresolved flags still opens Default View and shows a compact review status linking to Import Info.
- Difficulty and Personal rating precede Collections and Tags.
- Collections and Tags remain bounded and disclose overflow through `+N`.
- Media and Import Info share one auxiliary slot and use equal-width bottom sheets.
- Media and Import Info do not link to one another internally.
- Panel close and preview close use a cross; resource deletion uses a trash icon.
- Recipe deletion remains in overflow and uses a blocking confirmation.
- Cooking Focus has no ingredient or instruction checkboxes and no portion multiplier in this scope.

## Mobile shell and viewport range

The primary evaluation viewport is `390 × 844`. The layout must also remain usable at 360 px and 430 px widths without horizontal overflow.

The prototype toolbar is an evaluation control outside the simulated product surface. It allows reviewers to select scenario, context, role, and mock deletion result. It must not be mistaken for product navigation.

The product surface uses one readable column and preserves native page scrolling. Touch targets are at least 44 CSS pixels where practical. Focus indicators remain visible.

## Default View

### Compact header

The header contains:

- a compact cover or explicit no-cover state;
- recipe title;
- source identity row for imported recipes, for example `Instagram video · Marta Cooks`;
- cooking-facts row, for example `45 min · 4 servings`.

Long titles may wrap to three lines without hiding the actions. Manual recipes omit source identity without leaving an empty placeholder.

### Main actions

Use two horizontally arranged rows:

```text
[View] [Focus] [Edit]
[Media · N] [Import info] […]
```

- The active mode is visually and semantically indicated.
- `Media · N` is hidden when no media exists.
- `Import info` is hidden for manual recipes.
- The groups wrap only between groups, not through arbitrary button compression.
- Selecting `Edit` keeps the user in the current context and announces `Edit Mode is being designed.` No incomplete editor is opened.

### Review status

The status appears only when unresolved import flags exist. It is proportional to its content rather than a full-width warning banner and includes a clear `Review import` action.

The status summarizes the number of messages but does not pretend that flags map to individual recipe fields.

### Secondary metadata

Render the group in this order:

1. Difficulty and Personal rating;
2. Collections;
3. Tags.

Collections and Tags show a fixed number of readable values followed by `+N`. Activating `+N` opens a small mobile disclosure sheet for that metadata set. It does not enter Edit Mode or Organize Recipe.

### Reading content

Sections are separated through headings, spacing, and dividers rather than repeated cards.

- Ingredients show at most 12 items initially.
- Instructions show at most 8 steps initially.
- Cooking Notes show at most 4 lines initially.
- Each long section expands and collapses independently.
- Estimated Nutrition follows Instructions on mobile so the main recipe reading order is not interrupted by the desktop column grouping.
- Cooking Notes follow Estimated Nutrition.

Expanding or collapsing one section must not reset another section or scroll the page to the top.

## Cooking Focus

Cooking Focus is a simplified execution context.

Show:

- compact title;
- cooking facts;
- the same two-row main-action model;
- a sticky `Ingredients / Instructions` switch;
- the selected recipe section;
- Cooking Notes after Instructions when the Instructions view is active.

Hide:

- cover;
- source identity;
- review status;
- difficulty, rating, Collections, and Tags;
- nutrition as a primary section;
- provenance, resource status, and administrative information.

The switch changes only Focus content. It does not reset page state, Media selection, or the stored Default View position.

Selecting View returns to the previous Default View scroll position. Selecting Edit shows the neutral in-progress announcement without leaving Focus.

## Media bottom sheet

Media is closed by default and opens from View or Focus in the shared auxiliary slot.

The sheet contains:

- drag handle;
- title with total media count;
- cross close control;
- selected image preview;
- caption, origin, and current-cover marker where useful;
- thumbnail choices;
- understandable external video or link actions.

Raw URLs, resource IDs, extraction flags, debug information, and deletion controls do not appear.

The sheet supports downward-swipe dismissal. Content scrolling takes precedence until the sheet is scrolled to its top. Closing returns focus to the Media trigger and preserves the underlying page position and Focus selection.

## Import Info bottom sheet

Import Info uses the same width and vertical behavior as Media. Only one auxiliary sheet can exist at a time. Because the mobile sheet covers the main action row, switching panels requires closing the current sheet and then choosing the other main-page action; the sheets never stack and contain no internal cross-navigation.

The sheet contains, when applicable:

- general review messages;
- one `Mark all reviewed` action;
- imported-resource groups organized by primary resource;
- derived resources nested under their primary resource;
- recognizable image thumbnails;
- conditional `Ignored resources` grouping;
- compact removed-resource type summary;
- eligible debug information only when the prototype role is Debug.

Do not show an extracted-recipe duplicate, `Provenance`, `Original source`, field-level conflict choices, or Restore actions.

### Review action

`Mark all reviewed` changes review state only. It does not modify the saved recipe or imported resources. After completion, the review status disappears from Default View and a live announcement confirms the result.

### Resource deletion

- Every removable primary or derived resource uses a trash icon.
- Removing a derived resource replaces that row with an inline confirmation.
- The confirmation states that the resource cannot be restored and the saved recipe will not change.
- Removing a primary resource uses a confirmation inside that resource group.
- The primary confirmation lists the number and types of derived resources that will also be deleted.
- A derived resource used as the current cover is explicitly retained.
- Cancelling, pressing Escape, or switching away restores the unconfirmed resource state.

## Overflow and recipe deletion

Overflow opens an anchored mobile menu or compact action sheet with rare actions. `Delete recipe…` is the final separated destructive item.

Selecting it opens a blocking bottom sheet that:

- names the recipe;
- states that deletion cannot be undone;
- explains that associated imported files, images, and links are also deleted;
- includes a cross, Cancel, and `Delete recipe`;
- cannot be dismissed by a downward swipe.

Mock success returns to a Recipes-list destination and announces `Recipe deleted`. Mock failure keeps the confirmation open and shows `Recipe couldn’t be deleted. Try again.`

## State preservation

The prototype keeps separate state for:

- Default View scroll position;
- current Focus tab;
- expanded Ingredients, Instructions, and Notes sections;
- selected Media item;
- Media and Import Info sheet scroll positions;
- reviewed flags;
- removed-resource mock state;
- pending destructive confirmation.

Opening or closing a non-destructive sheet preserves the underlying context. Only one auxiliary sheet can be open. Closing Import Info cancels any unconfirmed resource action before the user can open Media from the main action row.

## Required scenarios

The scenario control must expose:

1. normal imported recipe without flags;
2. imported recipe with unresolved flags and ignored resources;
3. manual recipe without Import Info;
4. long title with no cover;
5. dense metadata with 50 Tags and 20 Collections;
6. long content with 45–50 ingredients, 35–40 steps, and long notes;
7. loading recipe;
8. failed recipe load;
9. missing recipe.

The prototype role control exposes User and Debug roles. The mock delete-result control exposes success and failure.

## Accessibility behavior

- Mode controls expose the active context through `aria-current` or equivalent semantics.
- Bottom sheets use dialog semantics and have an accessible name.
- Blocking deletion uses `aria-modal="true"`; background content is inert.
- Focus moves to the sheet heading or close control on open and returns to the trigger on close.
- Escape closes non-destructive sheets and cancels inline confirmations before closing their parent sheet.
- Focus remains trapped inside blocking modal sheets.
- Status changes are announced through a live region.
- Icons have accessible names through their buttons; decorative SVGs remain hidden.
- Swipe gestures always have equivalent cross or Cancel controls.
- Color is not the only signal for warnings, active modes, review status, or destructive actions.

## Visual direction for this iteration

This remains a serious low-fidelity product prototype rather than polished final UI.

- Use a cool neutral canvas, white reading surface, deep blue-gray text, restrained blue action emphasis, amber review status, and red only for destructive actions.
- Use a compact product-oriented sans-serif hierarchy.
- Prefer dividers and whitespace over repeated cards or heavy shadows.
- Keep border radii and elevation limited to overlays and touch affordances.
- The distinctive mobile signature is the transition from calm sequential reading to one consistent family of bottom sheets without losing reading position.

## Prototype artifact

Create a new isolated iteration under:

```text
design/recipe-detail/prototypes/06-mobile-recipe-detail/
```

Expected files:

```text
index.html
styles.css
data.js
app.js
test_prototype.js
README.md
PLAN.md
assets/
```

Reuse mock data and local SVG assets from Prototype 05 only when they still match the approved decisions. Do not import Prototype 05 JavaScript or CSS as a runtime dependency; the mobile prototype must remain understandable and independently testable.

## Verification and evidence

Browser verification covers:

- `390 × 844` normal, flagged, Focus, Media, Import Info, and delete-confirmation states;
- 360 px narrow-width overflow and touch-target checks;
- 430 px wide-mobile layout;
- long-title and dense-content scrolling;
- manual-recipe conditional actions;
- loading, failed, and missing states;
- keyboard focus, Escape, sheet focus return, and blocking-dialog focus trap;
- swipe-down dismissal for Media and Import Info but not recipe deletion;
- no console errors, broken local assets, or horizontal overflow.

Capture screenshots under:

```text
design/recipe-detail/screenshots/06-mobile-recipe-detail/
```

Record separate UX, visual, product-fit, accessibility, and responsive/long-content reviews under:

```text
design/recipe-detail/reviews/06-mobile-recipe-detail/
```

## Out of scope

- functional Edit Mode;
- production implementation;
- production data or APIs;
- global application navigation redesign;
- polished final visual system;
- ingredient or instruction checkboxes;
- portion scaling;
- persistent cooking sessions;
- embedded video;
- step-level media mapping;
- Organize Recipe and Cover Picker workflows beyond their existing entry-point implications.

## Approved mobile header amendment — 2026-07-24

This amendment supersedes the earlier two-row mobile action model and the earlier description of Import Info as a sibling auxiliary panel opened from the visible main actions.

The expanded mobile header has three levels:

```text
[Back]                                      [Media] [...]
[cover]  title / source identity / cooking facts
[View]              [Focus]              [Edit]
```

After scrolling, it collapses to one sticky row:

```text
[Back]  truncated recipe title                 [Media] [...]
```

- Media remains available when no media exists and opens an empty state with a path to Manage Media; this includes manual recipes.
- The Media icon always opens the Media bottom sheet. It never opens a combined resource chooser.
- Overflow opens a mobile bottom sheet whose first row contains `View / Focus / Edit`.
- For imported recipes, the remaining Overflow items are `Import info`, Export, and the final separated destructive Delete action. Manual recipes omit `Import info`.
- Import Info opens as its own dedicated bottom sheet or full-height mobile section. It is an administrative destination, not a tab within Media.
- Media and Import Info contain no internal navigation or switching control to one another.
- Desktop behavior is unchanged: Media and Import Info remain separate drawer entry points.

Only Import Info is omitted for manual recipes. The mobile unresolved-import status spans the full Recipe Detail width; the compact proportional treatment remains the desktop rule.

The full-width mobile status uses compact vertical padding and leaves a clear gap before secondary metadata. While unresolved flags remain, a notification dot appears on Overflow and again on the `Import info` item inside the Overflow sheet. The controls expose `import review needed` in their accessible names, and both dots clear after `Mark all reviewed`. The dot is a review-state indicator, not a warning icon on Import Info.

## Approval state

- Overall mobile-first sequential approach: approved.
- Visible but non-functional Edit entry with neutral in-progress announcement: approved.
- Written specification: awaiting user review.
