# Edit Mode Current Decisions

Status: approved structural direction; visual styling remains open  
Last updated: 2026-08-13

## Editing model

- Edit Mode is one page with wide editing sections and one recipe-level draft.
- Desktop uses a persistent left section rail with section counts and validation state.
- Mobile uses the approved always-compact Recipe Detail header and a single-open accordion for Basics, Ingredients, Instructions, Cooking notes, and Estimated nutrition. It does not use a separate current-section index.
- Mobile `Save` is the persistent contextual action in the compact top toolbar. The former fixed bottom `Cancel / Save changes` bar is rejected.
- While mobile Edit is active, `Save` replaces the direct Media utility; Media and Import Info remain available from Overflow.
- Mobile Back owns exit. When the Recipe Edit draft is dirty, Back opens the unsaved-changes guard instead of silently discarding changes.
- The approved mobile guard is a blocking bottom sheet titled `Unsaved changes` with `Save changes`, destructive-only `Discard changes`, and neutral `Keep editing`.
- Close, Escape, backdrop, downward swipe, and system Back dismiss the guard safely and keep the draft. Saving validates the whole draft; a failed validation returns to the linked summary and cancels navigation.
- The guard applies to page/browser Back, View/Focus, global navigation, the central Add action, and entry into Manage Media. Opening Media or Import Info does not leave Edit and does not invoke it.
- The mobile global navigation remains visible and unchanged below the editor. It contains navigation only and never absorbs recipe-edit actions.
- Ingredient notes are not shown or edited.
- Form controls use content-based maximum widths and do not stretch across the full editor without a reason.

## Approved desktop Basics and Ingredients

- Desktop Basics uses two semantic zones without card containers: Recipe identity on the left and Cooking facts & assessment on the right.
- Recipe identity contains Title, fixed Source, and Author.
- Cooking facts & assessment contains compact Cooking time, Servings, Difficulty, and Personal rating controls.
- Cooking time edits only the numeric value and displays `min` as a fixed suffix. Cooking time and Servings may be empty; when present, each must be a positive whole number. Quantity retains the approved decimal, fraction, and range syntax.
- Difficulty is a visible `Easy / Moderate / Hard` segmented single-choice group with a separate `Clear` action for the unset state.
- Personal rating is a whole-star `1–5` single-choice group with visible text such as `4 of 5`; half stars are unsupported. A separate `Clear` action returns it to Not rated.
- Desktop Ingredients remains a compact editable row layout: reorder handle, optional Quantity, fixed-dictionary Unit, required Ingredient name, and trash action.
- Ingredient notes are absent. A new ingredient starts with empty Quantity and `No unit`.
- Desktop page scrolling and rail navigation coexist. Scrollspy updates the active rail section without moving focus or scrolling on its own.
- Recipe Edit has one global `Save changes` / `Cancel` pair; sections do not save independently.

## Approved desktop validation and guard

- Invalid numeric syntax and overlength errors appear once present; missing required values appear after blur or Save.
- Aggregate errors such as more than 50 ingredients appear at section level and in the failed-Save summary.
- Failed Save shows an overall linked summary, marks every affected rail section, and moves focus to the first invalid field.
- The desktop dirty-draft guard is a centered blocking dialog: `Unsaved changes`, `Save changes before leaving this recipe?`, and `Save / Discard / Cancel`.
- The guard applies to Back, browser Back, View/Focus, other navigation, and entry into Manage Media. Media and Import Info auxiliary panels do not trigger it.

## Approved mobile validation and guard

- Mobile uses the same hybrid validation timing and recipe-level draft boundary as desktop.
- A failed Save places a focusable linked error summary above the accordion sections.
- Summary links open and focus the affected field or section; accordion headers expose non-color-only error counts.
- Ingredient-sheet errors remain local to the ingredient sub-draft. `Done` keeps the sheet open and focuses its first invalid field.
- The 50-ingredient maximum is a section-level error and is also represented in the failed-Save summary.
- Cooking time is labelled `Cooking time (min)` and contains only the editable numeric value.
- Cooking time and Servings accept an empty value or a positive whole number. Quantity accepts numeric expressions such as `2`, `1.5`, `1,5`, `1/2`, `½`, and `1–2`.
- Obviously invalid syntax is reported immediately. Plausible incomplete syntax such as `1/` waits until blur, `Done`, or Save.

## Auxiliary panels while editing

- Media and Import Info retain the one-auxiliary-slot model.
- Opening Media or Import Info does not leave Edit Mode and does not trigger a navigation guard.
- Media remains the same read-only panel in View, Focus, and Edit.
- Opening, replacing, or closing an auxiliary panel preserves the unsaved Recipe Edit draft, active section, and scroll position.
- When enough editor width remains, the desktop rail stays visible beside a nonmodal drawer.
- If the drawer leaves insufficient editing width, the rail becomes the compact section selector.
- On narrower desktop widths, the drawer overlays an unchanged inert editor.
- Unconfirmed destructive panel state is cancelled when the panel closes or is replaced.

## Manage Media

- `Manage media` is a separate full-screen editing workspace on mobile and desktop, not an Edit Mode panel state.
- The read-only Media panel is its entry point from View, Focus, and Edit.
- Manage Media owns a separate draft with `Save media changes` / `Cancel` and contains image capacity, upload, cover selection, image removal, and external media links.
- External links are read-only in Manage Media; their resource lifecycle stays in Import Info.
- The current cover cannot be removed until another image or the default cover is selected.
- Failed validation or upload does not partially remove existing images or change the cover.
- Entering Manage Media from a dirty Recipe Edit draft leaves Edit Mode and therefore uses the approved desktop navigation guard.

## Import Info actions while editing

- Import Info opens over Edit Mode without a guard and does not become part of the Recipe Edit form.
- Removing an imported resource is an immediate resource action independent of global Recipe Edit `Save changes`.
- The approved inline confirmation remains next to the affected primary or derived resource and states that removal takes effect immediately and cannot be undone.
- Resource removal does not change the saved recipe or the unsaved Recipe Edit draft. The current-cover exception remains in force for cascade deletion.
- After successful removal, Import Info updates in place; closing it returns to the same Recipe Edit section and scroll position with the draft intact.
- A failed resource removal keeps Import Info open, reports the failure beside the action, and leaves the Recipe Edit draft unchanged.

## Ingredient Unit

- Quantity remains a compact free-text value.
- Unit comes from one fixed, localized dictionary; arbitrary values cannot be saved.
- The approved interaction is corrected option A: selecting Unit expands the active ingredient row to show autocomplete search and available chips.
- The initial chip list has a fixed visual limit followed by `+N`; the working orientation is 8 visible chips on desktop and 6 on mobile.
- Typing filters chips by abbreviation, full label, and localized aliases. During filtering, `+N` is hidden.
- On mobile, the expanded selector spans the full editor width beneath the ingredient row. It is not indented beneath the Quantity and Unit fields.
- Selecting a chip updates the local recipe-edit draft and closes the selector. Escape or clicking outside preserves the previous value.

## Mobile Ingredients

- Mobile uses a compact one-line ingredient list instead of exposing Quantity, Unit, and Ingredient inputs in every row.
- Each row keeps a readable ingredient-summary button with a chevron and the standard trash action. Mobile has no DnD, reorder handle, reorder instruction, or accessible move commands.
- The approved editor entry is option A: the summary area is one large button with a chevron. A separate pencil button and an overflow-only entry are not used.
- Activating the summary opens a bottom sheet dedicated to that ingredient. The sheet edits Ingredient, Quantity, and Unit, including the approved fixed-dictionary Unit autocomplete.
- `Done` applies the ingredient sub-draft to the unsaved Recipe Edit draft; only the global `Save changes` action persists the recipe.
- The same sheet opens empty for `Add ingredient`.
- The sheet has a cross and supports downward-swipe dismissal when unchanged. If ingredient values changed, dismissal requires a discard decision.
- The trash action removes the ingredient from the Recipe Edit draft. Desktop ingredient reordering and instruction reordering are unchanged and outside this mobile decision.

## Mobile Basics refinement

- Basics contains seven fields: Recipe title; Source; Author; Cooking time; Servings; Difficulty; and Personal rating.
- Recipe title occupies one full-width row. Source / Author, Cooking time / Servings, and Difficulty / Personal rating use three equal two-column rows with consistent control height.
- Source is a fixed select: Manual, Instagram, Threads, TikTok, Other.
- Difficulty is a fixed select: Not set, Easy, Moderate, Hard.
- Personal rating is a fixed select: Not rated and 1–5 out of 5 in whole-number steps.
- Difficulty and Personal rating persistence remain future backend work.
- The approved mobile control treatment is hybrid: Source opens a checked selection bottom sheet, Difficulty uses three direct segments, and Personal rating uses five whole-value stars.
- The five-star group is horizontally centered in its full-width rating area. `Clear` remains a separate action aligned with the field heading.

## Related artifacts

- Persistent visual overview: `../prototypes/00-decision-gallery/index.html`
- Captured Edit Mode decisions: `../screenshots/edit-mode/`
- Approved auxiliary-context behavior: `09-edit-mode-auxiliary-context-behavior.md`
- Approved mobile validation and guard: `../prototypes/16-mobile-edit-validation-and-guard/index.html`
- Approved desktop Basics, Ingredients, validation, and guard: `../prototypes/17-desktop-edit-basics-validation-and-guard/index.html`
- Temporary `.superpowers` source iterations are not part of the design handoff; all approved behavior is represented by the permanent decision, prototype, screenshot, and review artifacts above.

## Still unresolved

- The exact Unit dictionary, aliases, and localized ordering.
- The exact pixel threshold where the desktop section rail becomes compact.
- The detailed mobile and desktop layout of the separate Manage Media workspace.
- Final typography, color, iconography, focus, hover, error, and selected states.
- Validation and error recovery for Instructions, Cooking notes, and Nutrition, plus sparse/dense data and localized-label stress tests.
- Save request in-progress, success, and server-failure presentation.
- Mobile software-keyboard behavior while editing fields and sheets.
