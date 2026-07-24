# Recipe Detail v3 — Panel and Resource Refinement

Status: Approved for low-fidelity prototyping  
Approved: 2026-07-23

## Scope

Refine only three unresolved interactions in the isolated Recipe Detail prototype:

1. compare the existing action placement A with a corrected placement B;
2. make imported images identifiable and keep cascade confirmation adjacent to its resource group;
3. define Media and Import Info as two contents of one auxiliary-panel slot in Cooking Focus.

All previously approved Recipe Detail decisions remain fixed. This is not production implementation or high-fidelity styling.

## Header variants

### A — Under title

The horizontal `View / Focus / Edit / Import info / Overflow` row starts at the title column.

### Corrected B — Full header width

The same horizontal row appears below the cover/title/metadata row and starts at the cover's left edge. The compact review status below it uses the same left alignment. Buttons never become a vertical cover-side stack.

Both variants must use identical content and dimensions for comparison.

## Imported image resources

- Image children have a visible thumbnail, label, state, and current-cover marker where applicable.
- A thumbnail expands an image preview inline within the same resource row/group; no second drawer opens.
- Text, transcript, and link resources do not receive fake image previews.
- Prototype thumbnails are local low-fidelity SVG assets, not generated images and not production imagery.

## Cascade deletion

- Selecting `Remove` on a primary resource hides that trigger and expands a confirmation block inside the same group.
- The block appears directly below the primary row and before the derived children.
- It states affected counts by type and the current-cover exception.
- Derived rows that would be removed are visibly marked; the current cover remains explicitly protected.
- `Cancel` is the safe initial focus; `Escape` cancels the pending confirmation.
- Switching away from Import Info cancels an unconfirmed destructive action.

## Shared auxiliary-panel slot

- Cooking Focus owns at most one auxiliary panel/sheet.
- `Media` and `Import info` switch the content of that slot instead of stacking panels.
- When both are available, the open panel exposes a `Media · N / Import info` context switch.
- Switching preserves each panel's own scroll and Media selection/expansion state.
- Closing the slot returns to the same Cooking Focus position.
- Desktop uses the existing drawer behavior; tablet and mobile switch content inside the same modal drawer/bottom sheet.

## Approval still required

- Choose A or corrected B after browser comparison.
- Approve or revise the visual density of image rows and inline cascade confirmation.
