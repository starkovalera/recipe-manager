# Design graph

This directory owns the repository-readable input for Design Operations
projections. The graph is authoritative only for stable visual identity and
relationships; decisions, GitHub, and roadmaps remain authoritative for their
respective facts.

## First map boundary

Issue [#95](https://github.com/starkovalera/recipe-manager/issues/95) contains
the bounded Recipe Detail desktop First map:

- `graph.json` records version, sources, and precedence;
- `domains/recipe-detail-first-map.json` authors three journeys, 11 current
  screen/state nodes, and labeled transitions;
- `snapshots/github.json` caches representative task and pull-request state;
- `../pen/inputs/recipe-detail-first-map.json` is the deterministic normalized
  input consumed by the optional Pen projection.

The normalized JSON remains usable if Pen is removed. It contains no Pen node
IDs, layout coordinates, credentials, or inferred approval state.

## Core map boundary

Issue [#90](https://github.com/starkovalera/recipe-manager/issues/90) extends
the same desktop Recipe Detail slice into the current Core checkpoint:

- `domains/recipe-detail-core-map.json` is the active 27-node graph input;
- `../pen/inputs/recipe-detail-core-map.json` is its deterministic normalized
  projection input;
- the graph keeps the three journeys separate: Read / Focus, Edit / Save, and
  Resources / Media;
- nine unfinished areas remain explicit placeholders, and the two known source
  contradictions remain `verification_needed` for #91;
- the Core map is desktop-only, derived, and does not decide the final Pen role
  or authorize production implementation.

The First map remains a historical 11-node artifact for the #95 checkpoint. It
is not overwritten by the Core expansion.

## Source precedence

1. The latest applicable decision document and decision log own Design state.
2. The cached live GitHub snapshot owns issue and pull-request Delivery facts.
3. Canonical roadmaps own scope and release boundaries.
4. Evidence files prove what was reviewed but do not assign status.
5. When authoritative sources disagree, generation emits
   `verification_needed`; it never guesses which fact is current.

## Generate and validate

```powershell
node scripts/design-ops/generate-first-map.mjs
node scripts/design-ops/validate-first-map.mjs

node scripts/design-ops/generate-core-map.mjs
node scripts/design-ops/validate-core-map.mjs
```

Generation is deterministic for the committed sources. The First-map and
Core-map validators intentionally remain separate because their node-count
contracts differ. Refreshing GitHub state is an explicit lifecycle action and
must update `asOf`, `sourceRevision`, and the affected records together.
