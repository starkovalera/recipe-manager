# Recipe Detail Approved UX Foundation

Status: approved for reuse and visual development  
Approved: 2026-07-23

## Purpose

This document is the consolidated structural source of truth for Recipe Detail. Future Recipe Detail visual work must preserve it unless the user explicitly reopens a decision. Other product pages may reuse the transferable patterns identified in `../reusable-product-patterns.md`, but must not copy recipe-specific structure blindly.

When a historical artifact conflicts with this document, this document and the later explicit entries in `docs/ui-ux/07-decisions-log.md` win.

## Product character

Recipe Manager is a productivity tool for importing, reviewing, organizing, reading, and using recipes. It is not a recipe blog or lifestyle site.

The interface should be:

- compact without feeling cramped;
- calm during reading and cooking;
- explicit about destructive or irreversible actions;
- capable of dense, realistic data;
- structured through hierarchy and dividers rather than a card around every section;
- designed independently from the current production frontend appearance.

## Context model

Recipe Detail contains distinct task contexts:

```text
Recipe Detail
├── Default View
├── Cooking Focus
├── Edit Recipe
├── Organize Recipe
├── Cover Picker
└── One auxiliary slot
    ├── Media
    └── Import Info
```

Do not collapse these tasks into one long dashboard or a permanently visible form.

## Default View

### Header

- Use a compact, recognizable cover rather than a hero image.
- Recipe title is the strongest element.
- Source identity and cooking facts are separate rows:

```text
Instagram video · Marta Cooks
45 min · 4 servings
```

- Do not show visible `Source` or `Author` labels.
- The upper-right metadata order is:
  1. Difficulty and Personal rating;
  2. Collections;
  3. Tags.
- Collections and Tags expose a fixed number of values followed by `+N`; they never become an unbounded header cloud.

### Main actions

Corrected B is approved. The horizontal action band sits below the header and begins at the cover edge.

```text
[View] [Focus] [Edit]  |  [Media · N] [Import info] […]
```

- `View / Focus / Edit` are one semantic mode group.
- `Media / Import info / Overflow` are a separate resource/action group.
- Media appears in View, Focus, and Edit only when media exists.
- Import Info appears only for imported recipes and remains visually neutral.
- Overflow contains rare actions. `Delete recipe…` is its final separated destructive item.

### Review status

- Without unresolved flags, Default View opens normally and shows no warning.
- With unresolved flags, Default View still opens normally and shows a compact proportional status linking to Import Info.
- The neutral Import Info action has no warning icon.
- Flags are general import messages, not field-level conflicts.

### Reading layout

- Desktop uses a fixed-width Ingredients column and a wider Instructions column.
- Estimated Nutrition follows Ingredients.
- Cooking Notes follow Instructions.
- Initial visible bounds are 12 ingredients, 8 steps, and 4 lines of notes, each independently expandable.
- Avoid card repetition and preserve readable line lengths.

## Cooking Focus

- Keep View, Focus, Edit, Media, Import Info, and overflow reachable through the same main-action model.
- Hide the large cover, source identity, organization metadata, flags, debug information, and source management.
- Keep title, cooking facts, ingredients, instructions, and notes.
- Ingredient and step checkboxes are deferred.
- Portion scaling is deferred until a separate actual-portion scenario is designed.
- On mobile, Ingredients and Instructions use an intentional switch rather than compressed desktop columns.

## Media

- Media contains recipe images plus understandable external video/link actions.
- Do not present raw URLs as primary labels.
- Media is closed by default and never contains a route to Import Info.
- Keep one selected image, thumbnail choices, captions/origin, current-cover marker, and external cooking references.
- Do not show resource IDs, extraction flags, debug data, or deletion controls.

## Import Info

- Import Info is a drawer or mobile sheet over the current recipe context, not a duplicate recipe page.
- Do not show an extracted-result copy, `Provenance`, or `Original source`.
- Show general review flags with one `Mark all reviewed` action. This only changes review state.
- Show imported resources grouped by primary source and derived-resource hierarchy.
- Conditionally show `Ignored resources`; keep ignored children grouped by their primary source.
- Image resources require recognizable thumbnails and optional inline preview.
- Removed resources may be summarized by type, but cannot be restored.
- Eligible debug details remain secondary and role-gated.

### Resource removal

- Every removal entry point uses the same trash icon; close actions use a cross.
- Removing a primary source removes its derived resources except the current cover.
- Primary confirmation appears inside the source group, reports affected counts/types, preserves the cover exception, and explicitly states that saved recipe content will not change.
- Removing any secondary resource opens confirmation inside that resource row.
- Secondary confirmation states that restoration is unavailable and the saved recipe will not change.
- Cancel and Escape restore the untouched row. Confirmed resources move into the removed summary.

## Recipe deletion

- `Delete recipe…` is available from View, Focus, and Edit through overflow only.
- It never appears inside Media or Import Info.
- Deletion is irreversible and has no Undo.
- Confirmation names the recipe and, for imported recipes, states that imported files, images, and links are also deleted.
- Do not require typing the recipe title.
- Desktop uses a centered blocking dialog.
- Mobile uses a blocking bottom sheet with cross and Cancel, but no swipe dismissal.
- Success returns to the Recipes list and announces `Recipe deleted`.
- Failure keeps confirmation open and shows `Recipe couldn’t be deleted. Try again.`

## Responsive model

- `>=1360 px`: a 460 px auxiliary drawer occupies space on the right; the recipe becomes narrower and the underlying actions remain available.
- `761–1359 px`: the 460 px drawer overlays the unchanged page; the dimmed page is inert until the drawer closes.
- `<=760 px`: the auxiliary panel becomes a full-width bottom sheet and the main actions split into two semantic rows.
- Media and Import Info always use the same width at a given breakpoint.
- Mobile auxiliary sheets close with both a cross and downward swipe from a visible handle. Content scrolling takes precedence until scroll position is at the top.
- Closing or replacing an auxiliary panel preserves the underlying mode, reading position, and relevant panel state; unconfirmed destructive state is cancelled.

## Accessibility baseline

- All icon-only controls have accessible names and tooltips where useful.
- Focus indicators are visible and use `:focus-visible`.
- Blocking dialogs/sheets trap focus, make the background inert, support Escape, and return focus predictably.
- Destructive meaning is communicated through text and structure, not color alone.
- Mobile touch targets are at least 40 px in the prototype and should target 44 px in final UI.
- Respect reduced-motion preferences and safe-area insets.
- Preserve browser zoom and avoid horizontal overflow.

## Required states for future visual work

- imported recipe with and without flags;
- manual recipe;
- long title and no cover;
- dense Tags and Collections;
- long Ingredients, Instructions, and Notes;
- incomplete or missing nutrition;
- used, ignored, removed, and nested resources;
- primary cascade and secondary irreversible removal;
- Media with images and links;
- recipe deletion success and failure;
- debug-eligible role;
- loading, missing, and failed-load states;
- 1440, 1280, 1024, and 390 px viewports.

## Remaining open work

Structural UX is approved. Remaining work belongs to visual execution:

- typography and type scale;
- color system and semantic status colors;
- final icon family and weight;
- real cover and thumbnail treatment;
- surface, divider, focus, hover, and selected states;
- restrained motion;
- localized-label stress testing, especially the mobile action band.

Do not reopen the approved information architecture while exploring these visual axes.
