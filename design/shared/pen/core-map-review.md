# Recipe Detail desktop Core map review

Status: complete; owner chose `continue`

Issue: [#90](https://github.com/starkovalera/recipe-manager/issues/90)

## What is visible

The repository-owned Core input expands the First map into 27 canonical desktop
screen/state nodes across the three required journeys:

- Read / Focus — 8 nodes;
- Edit / Save — 10 nodes;
- Resources / Media — 9 nodes.

The derived Pen canvas and fixed export show 41 labeled transitions, separate
Design and Delivery axes, nine explicit unfinished placeholders, the two
`verification_needed` warnings, and a final owner checkpoint prompt. The
normalized input remains usable without Pen and preserves stable repository
IDs, source precedence, and evidence references.

## Evidence and critique

- UX: the three lanes make the primary read, edit, and auxiliary-resource paths
  scannable; return paths and destructive/dirty-state boundaries remain visible.
- Visual: the evidence-first dark atlas keeps status legible at full-map scale;
  dense lanes are intentionally a map, not a screen-by-screen prototype.
- Product fit: approved decisions and verified evidence are represented; the
  nine unapproved areas are placeholders instead of invented behavior.
- Accessibility: this is a static design artifact, so keyboard semantics,
  focus order, announcements, and contrast still require review in the future
  responsive-web handoff.
- Density: the full map is intentionally large. Review the exported image at
  full size or inspect individual lane/card groups; do not treat the overview
  as a production viewport.

Mobile, production code, headless regeneration, drift reconciliation, and the
final Pen-role decision remain outside this issue's scope.

## Time and remaining work

- Agent time recorded for this checkpoint: approximately 2 hours, including
  source preflight, graph/scripts, Pen construction, and visual QA.
- Human time was not timed. The owner reported that the fresh-open result was
  correct after several troubleshooting iterations.
- Persistence proof: the owner saved `recipe-detail-core-map.pen`, a byte-identical
  copy was opened as `recipe-detail-core-map-fresh-open-check.pen`, and Pen read
  all 17 evidence images from the local main checkout.
- Unexpected cost: Save As preserved 17 paths through the source worktree and
  Pen retained a stale recent-file/workspace mapping. The editor crashed while
  reopening the affected document, left background processes holding the MCP
  transport, and required a recoverable config reset plus an MCP rewrite from
  worktree-relative paths to repository-relative screenshot paths.
- Benefit: once repaired, the repository-relative image fills survived an
  independent fresh-open and the normalized repository input remained usable
  throughout recovery.
- Remaining work: publish the persisted document and checkpoint evidence, then
  hand the measured recovery cost to #96.
- Recommendation: treat the persistence cost as material evidence for #96;
  continue only if the visual value justifies explicit path validation and
  fresh-open checks in the maintained workflow.

## Owner decision

The visible Core map and persistence proof passed owner review. The owner chose
`continue`. This closes the Core-map checkpoint but does not decide the final
Pen role; #96 owns the controlled regeneration proof and the final
`adopted` / `optional` / `rejected` decision.
