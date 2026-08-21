# Recipe Detail desktop Core map review

Status: awaiting owner checkpoint

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
- Human time recorded in this run: 0 minutes; the owner Save As and fresh-open
  proof are still pending.
- Remaining work: save the visible Core canvas to the repository `.pen`, copy
  and fresh-open it from a new pathname, inspect the three lanes and selected
  image fills, then record the result here.
- Recommendation: continue to the persistence proof and then hand the result
  to #96 only after #91 supplies its controlled source correction. Do not
  interpret this map as a Pen adoption decision.

## Owner decision

The checkpoint remains open until the owner reviews the visible Core map,
actual time/cost, remaining work, and recommendation, then answers one of:
`continue`, `change scope`, or `stop`.
