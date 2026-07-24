# Edit Mode Current Decisions

Status: approved structural direction; visual styling remains open  
Last updated: 2026-07-24

## Editing model

- Edit Mode is one page with wide editing sections and explicit global `Save changes` / `Cancel` actions.
- Desktop uses a persistent left section rail with section counts and validation state.
- Mobile uses a compact current-section index. Activating it opens a navigational bottom sheet; selecting a section closes the sheet and moves to that section.
- Ingredient notes are not shown or edited.
- Form controls use content-based maximum widths and do not stretch across the full editor without a reason.

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
- Entering Manage Media from a dirty Recipe Edit draft leaves Edit Mode and therefore requires a navigation guard.
- The exact guard actions and copy remain unresolved; it must not silently discard recipe changes.

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
- Each row keeps a reorder handle, a readable ingredient summary, and the standard trash action.
- The approved editor entry is option A: the summary area is one large button with a chevron. A separate pencil button and an overflow-only entry are not used.
- Activating the summary opens a bottom sheet dedicated to that ingredient. The sheet edits Ingredient, Quantity, and Unit, including the approved fixed-dictionary Unit autocomplete.
- `Done` applies the ingredient sub-draft to the unsaved Recipe Edit draft; only the global `Save changes` action persists the recipe.
- The same sheet opens empty for `Add ingredient`.
- The sheet has a cross and supports downward-swipe dismissal when unchanged. If ingredient values changed, dismissal requires a discard decision.
- The reorder handle supports direct drag and accessible move commands; the trash action removes the ingredient from the Recipe Edit draft.

## Related artifacts

- Persistent visual overview: `../prototypes/00-decision-gallery/index.html`
- Captured Edit Mode decisions: `../screenshots/edit-mode/`
- Approved auxiliary-context behavior: `09-edit-mode-auxiliary-context-behavior.md`
- Companion source iterations remain under `../.superpowers/brainstorm/` as working-session evidence and are not the consolidated source of truth.

## Still unresolved

- The exact Unit dictionary, aliases, and localized ordering.
- The exact pixel threshold where the desktop section rail becomes compact.
- The exact dirty-draft guard actions and copy before entering Manage Media.
- The detailed mobile and desktop layout of the separate Manage Media workspace.
- Final typography, color, iconography, focus, hover, error, and selected states.
- Full Edit Mode validation, error recovery, sparse/dense data, and localized-label stress tests.
