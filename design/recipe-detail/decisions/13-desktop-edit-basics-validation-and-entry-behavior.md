# Desktop Recipe Edit: Basics, Validation, and Entry Behavior

Status: approved UX direction; low-fidelity visual treatment approved
Date: 2026-07-25
Scope: desktop Recipe Detail and desktop Recipe Edit only

## Purpose

This decision set consolidates the approved desktop structure for Recipe Edit, its first validation patterns, the unsaved-changes guard, and the desktop entry behavior for Import Info. It does not define production implementation or final visual styling.

## Recipe Edit model

- Recipe Edit is one page and owns one recipe-level draft.
- The page has one global `Save changes` action and one global `Cancel` action.
- Individual sections do not have independent Save actions.
- The global save model is required because the user is editing one object and validation can cross section boundaries.
- Immediate Import Info resource actions and the separate Manage Media draft remain outside the Recipe Edit draft.

## Desktop section navigation

- A sticky section rail remains visible on the left while the page scrolls.
- Clicking a rail item scrolls the page to that section.
- Ordinary whole-page scrolling remains available.
- Scroll position updates the active rail item as the next section reaches the active threshold.
- Scrollspy never moves keyboard focus and never moves the page on its own.
- Sections with errors retain an error marker and count even when another section is active.

## Basics structure

The approved structure is option A: two semantic zones without card containers.

### Recipe identity

- Title
- Source
- Author

### Cooking facts and assessment

- Cooking time
- Servings
- Difficulty
- Personal rating

The zones use a subtle vertical divider. Fields use content-based maximum widths rather than stretching across the entire editor.

### Fixed selections

- Source: `Manual`, `Instagram`, `Threads`, `TikTok`, `Other`.
- Difficulty uses a visible single-choice segmented control: `Easy`, `Moderate`, `Hard`. An adjacent `Clear` action returns it to the unset state; `Not set` is not presented as a segment.
- Personal rating: `Not rated`, then `1` through `5` in whole-number steps.
- Personal rating uses a five-star single-choice control with a visible numeric value such as `4 of 5`. Only whole-star values `1`, `2`, `3`, `4`, and `5` are available; half-star values are not supported. An adjacent `Clear` action returns it to `Not rated`.

### Numeric-entry rules

- Quantity may be empty.
- Servings follows the same numeric-entry validation as Quantity and may be empty.
- Cooking time may be empty. When present, its editable value uses the same numeric-entry validation as Quantity.
- Cooking time displays `min` as a fixed, non-editable suffix. The user edits only the numeric value.
- Accepted input consists of numbers and symbols used to express numeric values, for example `2`, `1.5`, `1,5`, `1/2`, `½`, and `1–2`.
- Letters, emoji, and unrelated symbols are invalid.
- A new ingredient starts with empty Quantity and Unit set to `No unit`.
- Ingredient name is required.

The exact maximum lengths for Title, Author, and Ingredient name are intentionally not defined in this iteration.

## Desktop Ingredients

- Ingredients remain visible as compact editable rows inside the continuous desktop page.
- Every row contains, from left to right: reorder handle, Quantity, Unit, Ingredient name, and the standard trash action.
- Ingredient notes are not shown or edited.
- Quantity is compact, optional, and uses the numeric-entry rules above.
- Unit uses the approved fixed-dictionary selector. Arbitrary Unit values cannot be saved.
- Ingredient name receives the remaining row width and is required.
- The trash action removes the row from the unsaved Recipe Edit draft. Persistence still requires global `Save changes`.
- Desktop supports direct drag reordering. The production interaction must also expose an accessible non-drag reorder path.
- `Add ingredient` creates a draft row with empty Quantity, `No unit`, and an empty required Ingredient name.
- A recipe may contain no more than 50 ingredients. Count validation is section-level and is also included in the overall failed-Save summary.

## Validation timing

The approved behavior is hybrid validation:

- Show invalid numeric syntax and overlength errors immediately once the invalid value is present.
- Show a missing required value after the field loses focus or after Save.
- Show aggregate constraints, such as exceeding the ingredient limit, at the section level.
- After a failed Save, show an overall error summary above the form.
- The summary links to each invalid field or affected section.
- Focus moves to the first invalid field after failed Save.
- The left rail marks every section that contains an error.
- Each error is expressed by field state and concise text; color alone is never the only signal.

### Approved examples

- Title exceeds a future configured limit: `Title is too long. Shorten it before saving.`
- Invalid Quantity: explain that only numbers and numeric symbols are accepted.
- Invalid Servings: use the same numeric guidance as Quantity.
- Invalid Cooking time: use the same numeric guidance and state that the unit is always minutes.
- Empty ingredient name: `Enter an ingredient name.`
- Ingredient count above 50: show the current count, maximum count, and required removal action at section level.

## Unsaved-changes guard

A blocking centered desktop dialog is used whenever a dirty Recipe Edit draft would be abandoned.

- Title: `Unsaved changes`
- Message: `Save changes before leaving this recipe?`
- Actions: `Save`, `Discard`, `Cancel`

The guard is triggered by:

- the page Back action;
- browser Back;
- switching to View or Focus;
- navigating to another page;
- entering the separate Manage Media workspace.

The guard is not triggered by opening Media or Import Info as auxiliary panels.

### Guard outcomes

- `Save` validates and saves the entire Recipe Edit draft, then continues the original navigation.
- If validation or the save request fails, navigation is cancelled and the relevant errors remain visible in Edit.
- `Discard` discards the entire Recipe Edit draft and continues the original navigation.
- `Cancel` closes the guard and keeps the user in Edit.

## Desktop Import Info entry

- Import Info is not a permanently visible page button in View, Focus, or Edit.
- It is an item under the recipe overflow menu (`...`) on desktop.
- Selecting the item opens the approved Import Info auxiliary panel.
- When unresolved import flags exist, the overflow control displays a notification dot.
- After the menu opens, the same action cue is shown beside the `Import Info` menu item.
- On the first entry into a flagged recipe, Import Info opens automatically.
- This automatic opening happens once per recipe visit. Closing the panel or switching View, Focus, and Edit does not open it again during that visit.
- Recipes without unresolved flags do not auto-open Import Info.
- Manual recipes do not expose import-only information, but Media remains available.

## Approved low-fidelity evidence

- Basics option A: two semantic zones.
- Full normal desktop page: compact Basics controls, editable desktop ingredient rows, subsequent sections, sticky rail, and global save bar.
- Difficulty and Personal rating: segmented `Easy / Moderate / Hard` plus whole-star `1–5`, each with a separate `Clear` action.
- Validation screen: Basics and Ingredients errors, overall summary, rail markers, and global save bar.
- Guard screen: centered blocking dialog with the approved short actions.
- Working visual companion: `.superpowers/brainstorm/1933-1784985097/content/desktop-validation-and-guard-v1.html`.
- Working full-page companion: `.superpowers/brainstorm/1933-1784985097/content/desktop-edit-full-page-v1.html`.

## Responsive implications

- This decision set covers desktop only.
- On narrower desktop widths, the two Basics zones may stack while preserving their semantic grouping.
- Auxiliary-panel responsive behavior remains governed by the approved one-slot panel rules.

## Explicitly not decided here

- Final typography, colors, icons, spacing, and motion.
- Exact maximum lengths for Title, Author, and Ingredient name.
- The exact Unit dictionary and localized aliases.
- The precise scrollspy activation threshold.
- The detailed Manage Media workspace.

## Approval record

- Two-zone Basics option A: approved.
- Sticky rail plus ordinary page scrolling and scrollspy: approved.
- One global Save for the Recipe Edit draft: approved.
- Hybrid frontend validation and error hierarchy: approved.
- Numeric validation for Quantity, Servings, and Cooking time: approved.
- Fixed `min` suffix for Cooking time: approved.
- Segmented Difficulty with a separate Clear action: approved.
- Five-star Personal rating with visible numeric value and a separate Clear action: approved.
- Compact desktop Ingredients rows with reorder, fixed Unit, required name, trash action, and no ingredient notes: approved.
- Desktop unsaved-changes guard: approved.
- Overflow-only desktop Import Info with first-entry auto-open for flagged recipes: approved.
