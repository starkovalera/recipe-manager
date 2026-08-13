# Reusable Product Patterns

Status: approved lessons from Recipe Detail  
Updated: 2026-07-24

These patterns may guide other Recipe Manager pages. Reuse the principle and interaction contract, not the Recipe Detail geometry or copy.

## 1. Separate modes from utilities

When a page has persistent task modes and contextual tools, show them as adjacent but visibly distinct groups.

```text
[Primary modes]  |  [Contextual resources] [Overflow]
```

Do not style a drawer opener as if it were a peer navigation tab.

## 2. One auxiliary slot

Use one shared slot for supplementary workspaces such as Media, Import Info, history, audit detail, or contextual help.

- Never stack competing drawers.
- On wide screens, allow the slot to occupy layout space only when the remaining content stays usable.
- On narrower screens, overlay the unchanged page and make it inert.
- On mobile, use a bottom sheet designed for touch rather than a compressed drawer.

The breakpoint must follow minimum usable content width, not a generic device name.

## 3. Conditional availability instead of disabled clutter

Hide context-specific actions when the underlying capability or data does not exist. Examples:

- no Media action when the object has no media;
- no Import Info for manually created objects;
- no ignored section when nothing was ignored.

Use disabled controls only when users benefit from learning that the capability exists and can understand how to enable it.

## 4. Stable dense metadata

Show a small fixed number of values and a count disclosure such as `+N`.

- Keep the containing header or row height stable.
- Preserve the strongest object identity and primary task.
- Expand via popover, sheet, or dedicated organization context.
- Do not create unbounded chip clouds.

## 5. Context-preserving status

When an object remains usable despite review work:

- open the normal object view;
- show a compact proportional status;
- link to the dedicated review workspace;
- keep the neutral review entry point visually neutral.

Do not redirect users into a review workspace unless the unresolved state blocks normal use.

## 6. Parent/derived hierarchy

When secondary artifacts belong to a primary source, preserve that relationship visually.

- Group children under their parent.
- Show recognizable previews for visual files.
- Explain cascade consequences where the deletion action occurs.
- Keep protected exceptions, such as a current cover, visible in the same hierarchy.

This pattern can apply to imports, attachments, generated derivatives, and conversion outputs.

## 7. Local irreversible confirmation

For deletion of one item in a dense list, replace or expand that item's row with confirmation.

- Keep the name and preview visible.
- State whether restoration is possible.
- State effects on the saved object.
- Offer explicit Cancel and destructive Confirm.
- Escape cancels and returns focus to the original action.

Avoid confirmations far from the selected item.

## 8. Global destructive actions in overflow

Object-level deletion belongs in the page overflow rather than the permanent primary action band.

- Put it last and separate it from neutral actions.
- Use a trash icon plus explicit text.
- Open a blocking confirmation that names the object and explains scope.
- Do not promise Undo when the lifecycle cannot restore the object.
- On failure, keep context and provide a concrete retry path.

## 9. Consistent icon semantics

- Cross: close or dismiss a surface.
- Trash: remove a resource or object.
- External-link icon: open an external reference.
- Ellipsis: rare object actions.

Do not reuse a cross for deletion or mix text and icon deletion entry points at the same hierarchy level.

## 10. Explicit responsive state preservation

Before opening any drawer, sheet, dialog, or mode, define what must survive closing or replacement:

- underlying mode;
- page and panel scroll positions;
- selected item;
- temporary task state;
- unconfirmed destructive state.

Preserve useful state; cancel unsafe pending state.

## 11. Failure stays near the attempted action

If an action can be retried safely, keep the current confirmation or workspace open and show a concrete next step. Avoid navigating to a generic error page.

## 12. One hierarchy-aware mobile application shell

Use a stable mobile shell across ordinary application screens while allowing the top bar to express screen hierarchy.

- Root destinations show a title and contextual actions without Back.
- Nested and detail screens show Back; after scroll they collapse to Back, a truncated title, and essential contextual actions.
- Expanded detail headers may add an identity block and local modes beneath the utility row.
- A fixed bottom bar owns only global destinations and the central creation action.
- Screen-specific tools remain in the top bar or local Overflow instead of entering global navigation.
- One modal sheet layer opens above and fully covers the global bar; modal surfaces replace rather than stack.
- Focused creation and other explicit task flows may temporarily hide the global bar when Back or Cancel owns exit and dirty-state protection.

For the approved destination order and Recipe Detail instance, see [`decisions/11-global-mobile-shell.md`](decisions/11-global-mobile-shell.md).

## Recipe-specific patterns that are not universal

Do not automatically reuse these elsewhere:

- fixed Ingredients/Instructions columns;
- 12-ingredient and 8-step truncation thresholds;
- cooking-focused terminology;
- Media/Import labels;
- the exact 460 px drawer or 1360 px breakpoint.

Other pages must derive their own content hierarchy, thresholds, and minimum readable width.
