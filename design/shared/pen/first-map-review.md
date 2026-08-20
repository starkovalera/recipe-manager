# Recipe Detail desktop First map review

Status: awaiting owner fork decision<br>
Issue: [#95](https://github.com/starkovalera/recipe-manager/issues/95)<br>
Setup provenance: [#90 checkpoint 1](https://github.com/starkovalera/recipe-manager/issues/90#issuecomment-5356621586)<br>
Reviewed: 2026-08-20

## Result

The bounded First map represents 11 current Recipe Detail desktop screen/state
nodes in three visible journeys:

1. Read / Focus;
2. Edit / Save;
3. Resources / Media.

Every node carries a stable repository ID, current decision/prototype evidence,
representative issue/PR provenance, and independent Design and Delivery status.
The projection shows labeled directional relationships and explicitly states
that it is not an interactive prototype.

Artifacts:

- [`../design-graph/domains/recipe-detail-first-map.json`](../design-graph/domains/recipe-detail-first-map.json)
  — authored current-slice graph;
- [`inputs/recipe-detail-first-map.json`](inputs/recipe-detail-first-map.json)
  — normalized Pen-independent input;
- [`recipe-detail-first-map.pen`](recipe-detail-first-map.pen) — derived spatial
  projection;
- [`exports/recipe-detail-first-map.png`](exports/recipe-detail-first-map.png)
  — fixed owner-review export.

## Preserved decisions and boundaries

- Prototype 05 remains the current desktop evidence for Default View, Cooking
  Focus, Media, Import Info, and resource confirmation.
- Prototype 17 remains the permanent desktop evidence for Basics, Ingredients,
  validation, and the unsaved-changes guard.
- The map does not invent Instructions, notes, nutrition, Manage Media, or
  Organize behavior.
- Full Core expansion, headless regeneration, controlled drift correction,
  mobile, production code, and Pen adoption remain outside #95.

## Contradictions kept visible

- `warning.roadmap-pr80-state`: current Recipe Detail scope calls PR #80 draft,
  while the cached GitHub snapshot records it merged.
- `warning.import-review-contract`: approved Design uses `Mark all reviewed`,
  while the verified production audit records current per-flag PATCH behavior.

Affected nodes use `verification_needed`; generation does not choose a winner.

## Critiques

### UX

Pass. Three journey lanes provide a coherent overview, each node exposes its
purpose and status without opening details, and return paths prevent the linear
layout from implying one-way navigation. Cross-journey entry paths are named in
the footer.

### Visual

Pass for the spatial companion. The dark evidence-first treatment gives
screenshots enough contrast, uses restrained surfaces and no decorative recipe
blog styling, and keeps warnings visible without dominating every node. The
large canvas favors panoramic review over small-screen consumption, which is
appropriate for this desktop Pen experiment.

### Product fit

Pass. The canvas emphasizes productivity journeys, evidence, and source
contradictions. Cards are used only for actual screen/state nodes rather than as
generic page decoration. Pen is visibly secondary to repository sources.

### Accessibility

Pass for a static review artifact. Status meaning is written in text rather
than color alone, contrast is strong, and labels remain readable in the fixed
2800-pixel export. This does not claim keyboard or assistive-technology
interaction inside Pen; the projection is not an application UI.

### Density and long content

Pass for the selected 11-node slice. Stable IDs, long transition labels, and
status badges fit without clipping. The First map deliberately avoids the
20–30-node Core density question.

## Measured effort and unexpected cost

- Active #95 agent elapsed time to the review gate: approximately 40 minutes.
- New human time: 0 minutes; owner visual review is pending.
- Benefit: the normalized graph and validation path were straightforward, and
  the existing screenshots make the current desktop slice quickly legible.
- Unexpected cost: Pen 1.2.5 `Insert` nodes existed but rendered invisibly;
  visible `Copy` primitives were required. The MCP also lacks Save As, so the
  repository file required an opaque managed-file copy. These anomalies added
  roughly 15 minutes and are recorded in the Pen README.

## Remaining work after the fork gate

If the owner chooses `continue`, #90 may expand to the 20–30-node Core map while
#91 reconciles drift in parallel. #95 itself does not execute either task.

## Recommendation and requested decision

Recommendation: **continue**. The First map is coherent, source-owned inputs
survive without Pen, and the runtime anomalies are bounded enough to test in
Core rather than grounds for immediate rejection.

Owner decision required: `continue`, `change scope`, or `stop`.
