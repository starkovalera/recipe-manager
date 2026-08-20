# Recipe Detail desktop First map review

Status: owner chose `continue`; publication in draft PR #98<br>
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

The saved repository `.pen` was copied to a new pathname and opened through
Pencil as a fresh document. The reopened artifact contained three lanes, seven
resolved screenshot fills, and zero clipping problems. This specifically guards
against accepting an unsaved managed-canvas session as a repository artifact.

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

- Active #95 agent elapsed time to the initial review gate: approximately 40
  minutes; recovery and fresh-open verification added approximately 30 minutes.
- Human hands-on time was not timed; it was limited to visual inspection and
  the Save/Save As operations unavailable through MCP.
- Benefit: the normalized graph and validation path were straightforward, and
  the existing screenshots make the current desktop slice quickly legible.
- Unexpected cost: Pen 1.2.5 flat `Insert` nodes existed but rendered
  invisibly, and the MCP lacks Save As. The initial managed-file copy captured
  the unsaved welcome document rather than the visible atlas. The atlas was
  rebuilt as one nested repository-root tree and verified from a new pathname;
  these anomalies and the regression seam are recorded in the Pen README.

## Remaining work after the fork gate

The owner chose `continue`. After #95 closes, #90 may expand to the 20–30-node
Core map while #91 reconciles drift in parallel. #95 itself does not execute
either task.

## Recommendation and requested decision

Recommendation: **continue**. The First map is coherent, source-owned inputs
survive without Pen, and the runtime anomalies are bounded enough to test in
Core rather than grounds for immediate rejection.

Owner decision recorded: `continue`.
