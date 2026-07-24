# Edit Mode Auxiliary Context Behavior

Status: approved  
Approved: 2026-07-24

## Decision

Media and Import Info are auxiliary contexts available from Edit Mode. Opening either one does not leave Edit Mode, does not invoke a navigation guard, and does not make its actions part of the Recipe Edit draft.

The Recipe Edit draft, active section, and scroll position remain intact while an auxiliary panel opens, closes, or replaces the other panel.

## Media

- Media is the same read-only panel in View, Focus, and Edit.
- Media and Import Info continue to share one auxiliary-panel slot.
- `Manage media` is launched from the Media panel.
- Manage Media is a separate full-screen editing workspace on mobile and desktop.
- Upload, capacity, cover selection, image removal, and `Save media changes` / `Cancel` belong to Manage Media rather than Recipe Edit.
- Entering Manage Media leaves Edit Mode. A dirty Recipe Edit draft therefore requires a navigation guard and must never be silently discarded.

The exact guard actions and copy remain open for a later comparison.

## Import Info

- Import Info opens over Edit Mode without leaving it.
- Existing Import Info actions remain independent of global Recipe Edit `Save changes`.
- Removing a primary or derived resource takes effect immediately after its approved inline confirmation.
- The confirmation states that the action is immediate, cannot be undone, and does not change either the saved recipe or unsaved Recipe Edit changes.
- Cascade deletion continues to name affected resource counts and types. A resource retained as the current cover remains protected by the approved cover exception.
- After successful removal, the panel updates in place and the Recipe Edit draft remains unchanged.
- On failure, the panel stays open with a local error and the Recipe Edit draft remains unchanged.

## State boundaries

| State | Owner | Persistence action |
|---|---|---|
| Recipe content changes | Recipe Edit | Global `Save changes` |
| Media changes | Manage Media workspace | `Save media changes` |
| Import resource removal | Import Info | Immediate after inline confirmation |
| Unconfirmed panel deletion | Current auxiliary panel | Cancelled when the panel closes or is replaced |

## Superseded decision

This decision supersedes the earlier rule that opening Media from Edit Mode directly converted the panel into Manage Media. Media is now read-only in every recipe mode, and Manage Media has one consistent separate workspace across mobile and desktop.

## Preserved decisions

- Media and Import Info never stack.
- Both panels keep the same width at a given breakpoint.
- Import Info resource grouping, image previews, ignored resources, cascade confirmation, immediate non-restorable deletion, and current-cover protection remain unchanged.
- Recipe deletion remains a separate destructive recipe action and is not part of either auxiliary panel.
