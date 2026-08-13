# Main actions and responsive panels

Status: approved low-fidelity behavior foundation  
Updated: 2026-07-23

## Approved structure represented

- Corrected B is the sole current placement: actions start at the cover edge below the header.
- Modes and resources are distinct adjacent groups: `View / Focus / Edit` and `Media / Import info / Overflow`.
- Media appears in every recipe context when at least one image or cooking link exists.
- Media and Import Info occupy one equal-width auxiliary slot and contain no links to each other.
- Every panel/preview close is a cross; every resource-removal entry point is a trash icon.
- Ignored resources appear only when present and remain grouped by primary source.
- Every secondary-resource trash action opens an inline confirmation in that resource row. The copy states that restoration is unavailable and the saved recipe will not change.
- `Delete recipe…` is the final separated entry in the main overflow menu across View, Focus, and Edit.
- Recipe deletion uses a blocking desktop dialog or mobile bottom sheet. It names the recipe, describes the irreversible scope, and offers cross, Cancel, and `Delete recipe` without title entry or Undo.
- Media and Import Info do not contain recipe deletion controls.

## Responsive behavior

- `>=1360 px`: the 460 px drawer occupies space on the right; the recipe becomes narrower and main-page actions remain operable.
- `761–1359 px`: the 460 px drawer sits over the unchanged page; the dimmed page remains unavailable until the drawer closes.
- `<=760 px`: full-width bottom sheet; modes and resource actions use two rows.
- Mobile dismissal supports a cross, Escape with a keyboard, and downward drag from the handle. A drag closes after 96 px, or after 44 px with sufficient velocity. Reduced-motion preference removes the transition.
- The destructive recipe-deletion sheet is an exception: it has no swipe dismissal, preventing an ambiguous accidental close during confirmation.

## Rationale

Overlaying at narrow desktop widths avoids forcing the title, metadata, actions, ingredients, and instructions into the space remaining beside a 460 px drawer. Keeping Media in the main action row makes it discoverable before and after Cooking Focus and removes the need for panel-to-panel navigation.

## Unresolved

- Decide whether the mobile action group needs horizontal scrolling if localized labels become substantially longer.
