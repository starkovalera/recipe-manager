# Recipe Detail v4 — Visual Control Refinement

Status: Approved for low-fidelity prototyping  
Approved: 2026-07-23

## Header comparison

- Preserve both A and corrected B for later high-fidelity evaluation.
- A starts the horizontal action row at the title edge.
- Corrected B starts the same row at the cover edge below the top header row.
- Both variants use the same compact review-status maximum width of 620 px. Alignment is the only variable.
- Evaluate both with identical normal, flagged, long-title/no-cover, and mobile states.

## Imported-resource controls

- Expanded image preview closes with a small cross icon in its upper-right corner.
- Resource removal uses a trash icon; the primary cascade action keeps the explicit `Remove` text.
- Icon-only controls have descriptive accessible names, tooltips, visible focus, and 40–44 px hit targets.
- Cascade states use a two-column row: resource identity left, one consistently placed consequence label right.
- An expanded preview collapses when its primary resource enters cascade-confirmation state.

## Cascade warning copy

The confirmation explicitly separates recipe content from imported materials:

> Your saved recipe will not change. Ingredients, instructions, notes, and other recipe details will stay as they are.
>
> Only this source and 5 related imported resources will be removed: 1 transcript · 3 images · 1 text.
>
> The current cover will be kept.

## Auxiliary drawer

- Media and Import Info use the same width: 460 px wide desktop, 440 px tablet overlay, and full-width mobile sheet.
- Remove Media `Compact / Expand`; `Close` dismisses the slot.
- Remove the persistent Media / Import Info switcher.
- Media has an overflow menu containing the rare `Import info` action.
- Choosing it replaces Media with Import Info in the same slot and sets a contextual return target.
- Import Info shows `Back to media` only when entered from an open Media panel.
- Directly opened Import Info has no Media switch; closing and explicitly opening Media is acceptable for this rare path.
- Panel replacement preserves Media selection, panel scroll, and Cooking Focus position. Pending destructive confirmation is cancelled.

## Media contents

- Media separates `Images` from `Videos & links`.
- External links use descriptive action labels, platform/author context, and an external-link icon instead of raw URLs.
- Opening an external link does not own or reset Cooking Focus state.

## Remaining decision

Final A versus corrected B selection is deferred until both are evaluated with real typography, color, icons, and imagery.
