# V5 evaluation plan

- [x] Preserve approved content structure and corrected-B placement.
- [x] Separate recipe modes from resource actions.
- [x] Expose Media conditionally in every recipe context.
- [x] Remove Media-to-Import and Import-to-Media transitions inside panels.
- [x] Use cross icons for close and trash icons for all resource deletion.
- [x] Add conditional ignored-resource grouping with source association and previews.
- [x] Use one equal-width auxiliary slot.
- [x] Test nonmodal 1440, overlay 1280/1024, and mobile bottom sheet.
- [x] Test swipe-down dismissal, keyboard Escape, focus trapping, and overflow.
- [x] Capture screenshots and record separate critiques.

## Approved follow-up: secondary-resource confirmation

**Goal:** Require an explicit irreversible-removal confirmation for every derived resource without moving the user away from its row.

**Architecture:** Reuse the existing `state.pending` interaction state with a new `child` type. `resourceChildRow()` replaces only the selected row's trailing trash action with an inline confirmation; confirming moves the resource to `Removed resources`, while cancel/Escape restores the row and its trash action.

**Constraints:** Prototype-only files; no production changes; no Git operations; primary cascade behavior remains unchanged.

- [x] Add a failing browser assertion that clicking a normal child trash does not remove the row and instead shows `Remove this resource?`, `This resource cannot be restored.`, `Cancel`, and `Remove resource`.
- [x] Add the same assertion for an ignored image and verify its thumbnail remains visible during confirmation.
- [x] Implement `childConfirmation(child)` and the `pending.type === 'child'` branch in `resourceChildRow()`.
- [x] Replace immediate `data-remove-child` mutation with pending state; add `confirm-child`, cancel, and Escape behavior with focus restoration.
- [x] Style the confirmation as an inline full-row block, visually adjacent to the selected resource.
- [x] Update the decision log, v5 decision document, README, and review notes with the approved irreversible-removal rule and the approved 1360 px panel transition.
- [x] Run `test_prototype.js`; expect `MAIN_ACTIONS_RESPONSIVE_PANELS_CHECKS_PASS`, no console errors, and no horizontal overflow at 1440, 1280, 1024, or 390 px.

## Approved follow-up: delete recipe

**Goal:** Add a deliberately de-emphasized but consistently reachable irreversible recipe-deletion flow.

**Architecture:** The existing main-row overflow button opens a small anchored menu. `Delete recipe…` is the final separated destructive item. It opens a blocking confirmation dialog on desktop and a bottom sheet on mobile; success renders a mock recipe-list destination and status, while a selectable mock failure keeps the confirmation open with a next-step error.

**Constraints:** No production code, API calls, routing, or Git operations. Delete remains available from View, Focus, and Edit but never inside Media or Import Info.

- [x] Add failing assertions for overflow placement, separation, trash icon, and absence from Media/Import Info.
- [x] Add failing assertions for desktop confirmation copy, Cancel/Escape, and successful mock navigation.
- [x] Add failing assertions for mobile bottom-sheet confirmation and retained close/cancel paths.
- [x] Implement the anchored overflow menu with `Delete recipe…` as the final destructive item.
- [x] Implement a blocking `delete-recipe` layer with recipe-title copy, irreversible scope, Cancel, cross, and `Delete recipe`.
- [x] Add mock success and failure behavior; failure keeps the dialog open and offers `Try again` through the same destructive action.
- [x] Capture desktop menu, desktop confirmation, mobile confirmation, and failure screenshots.
- [x] Update decisions, README, and separate reviews.
- [x] Run `test_prototype.js`; expect `MAIN_ACTIONS_RESPONSIVE_PANELS_CHECKS_PASS` and clean production paths.
