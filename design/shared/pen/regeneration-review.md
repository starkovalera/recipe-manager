# Recipe Detail Core regeneration review

Status: evidence prepared; owner decision pending

Issue: [#96](https://github.com/starkovalera/recipe-manager/issues/96)
Delivery: draft [PR #103](https://github.com/starkovalera/recipe-manager/pull/103)

## Scope and inputs

This checkpoint evaluates the current desktop Core projection only. The
repository-owned graph and normalized input remain authoritative; the `.pen`
file and PNG are derived review artifacts.

- Current source snapshot: `design/shared/design-graph/snapshots/github.json`
  at `2026-08-22T15:03:22Z`, source revision
  `239fe6bd1c6c06d06c4593462efb8bd5ac68b471`.
- Core input: `design/shared/design-graph/domains/recipe-detail-core-map.json`.
- Normalized projection: `inputs/recipe-detail-core-map.json`.
- Derived projection: `recipe-detail-core-map.pen` and
  `exports/recipe-detail-core-map.png`.
- Controlled source baseline: the Core normalized input at `4b354a6^`, the
  parent of the merged #91 source correction in commit `4b354a6` / PR #99.

## Deterministic graph proof

The normalizer is shared by the generator and verifier so the proof exercises
the same transformation used to refresh the committed input. The commands
were run from a clean feature branch after the live snapshot was refreshed:

```powershell
node scripts/design-ops/generate-core-map.mjs
node scripts/design-ops/generate-core-map.mjs
node scripts/design-ops/verify-core-regeneration.mjs --before-ref '4b354a6^'
node scripts/design-ops/validate-core-map.mjs
node scripts/design-ops/validate-core-map.mjs --without-pen
```

Results:

- two identical-input runs produced the same normalized SHA
  `22ef5098200f1fe40baa5f15802db64dd9ebc2359b3952d8520c92de4ee9d075`;
- semantic Core SHA is
  `fee0af61a9ad8abe2a91086884a52ce340db2ad921b432269a82b73c8c3b71b3`;
- the Core contains 27 nodes, 41 transitions, 2 warnings, 9 placeholders,
  and 12 review screenshots;
- the controlled #91 change changed only
  `generatedFrom.asOf` and `generatedFrom.sourceRevision`; semantic nodes,
  statuses, provenance, transitions, placeholders, and warnings did not
  change;
- the Pen projection contains all 27 normalized stable graph IDs and 17 image
  fills;
- the graph and normalized input validate with `--without-pen`, proving that
  the repository-owned input does not require Pen artifacts.

The historical `node scripts/design-ops/validate-first-map.mjs` check remains
outside this scope and fails on the active 27-node Core selection with the
expected `First map must contain 8–12 nodes` and `normalized input lost a node`
messages. No First-map artifact was changed; this is the pre-existing validator
boundary recorded by the prior Core status work.

## Headless CLI boundary

The current supported package was checked without credentials:

```powershell
npm exec --yes --package="@pen.dev/cli@0.3.4" -- pen version
# pen 0.3.4
npm exec --yes --package="@pen.dev/cli@0.3.4" -- pen interactive `
  --in design/shared/pen/recipe-detail-core-map.pen `
  --out "$env:TEMP\recipe-manager-issue96\core-map-headless-copy.pen"
```

The package declares Node `>=22`; this checkout has Node `v24.18.0`. Both the
CLI status check and the headless interactive run reported that authentication
is required (`pen login` or `PEN_CLI_KEY`). No account, token, OTP, or API key
was supplied or persisted, and no generated `.pen` output was treated as
evidence. The temporary smoke directory was cleaned after the check.

Therefore the deterministic repository-input proof is complete, but a genuine
headless Pen open/save/export run remains a human prerequisite. The CLI path is
AI-backed rather than an offline renderer, so identical normalized input alone
does not establish identical Pen output without an authenticated run and a
fixed operation sequence.

## Effort and repair record

- Agent effort for this checkpoint: approximately 1 hour, including preflight,
  live snapshot refresh, CLI version/auth check, normalizer extraction, verifier,
  and documentation synchronization.
- Human effort for this checkpoint: 0 minutes; no Pen login or visual review was
  performed in this run.
- New manual repair: none. The prior Core checkpoint's 17 image-fill path repair
  and owner fresh-open proof remain recorded in
  [`core-map-review.md`](core-map-review.md).
- Temporary setup artifacts: none retained in the repository; no credentials or
  local configuration were changed.

## Recommendation and owner checkpoint

Recommendation: `change scope` for the Pen experiment and treat Pen as
`optional`. The repository graph and cockpit can be regenerated and validated
without Pen, while the current CLI requires account authentication and its
AI-backed path is not a deterministic offline renderer. The visual atlas may
remain a manually refreshed companion when its review value justifies the
setup, Save As, path, and fresh-open cost.

The owner must review this evidence and record exactly one final role decision:

- `adopted` — Pen requirements join cockpit automation and future domain tasks;
- `optional` — Pen remains a manually invoked companion and cockpit delivery is
  independent;
- `rejected` — retain the evidence and remove Pen from future acceptance
  criteria.

Until that response is recorded, #92 remains policy-held rather than natively
Pen-blocked, and #94 remains blocked by the unresolved #96 decision plus #92.
