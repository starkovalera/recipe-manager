# Pen projection

Pen is a derived spatial companion for the repository-owned Design graph. It is
not an approval surface, task tracker, or interactive prototype player.

## First map

Issue [#95](https://github.com/starkovalera/recipe-manager/issues/95) produces:

- `inputs/recipe-detail-first-map.json` — normalized, Pen-independent input;
- `recipe-detail-first-map.pen` — derived three-lane spatial projection;
- `exports/recipe-detail-first-map.png` — fixed visual review evidence.

The First map intentionally stops at 11 current desktop screen/state nodes. It
does not include the Core 20–30-node expansion, mobile, headless regeneration,
or a Pen adoption decision.

The setup provenance is recorded in the
[#90 checkpoint-1 comment](https://github.com/starkovalera/recipe-manager/issues/90#issuecomment-5356621586).

## Refresh boundary

1. Refresh the repository graph and cached GitHub snapshot from authoritative
   sources.
2. Run `node scripts/design-ops/generate-first-map.mjs` and
   `node scripts/design-ops/validate-first-map.mjs`.
3. Update the `.pen` projection only from the normalized input.
4. Save the repository `.pen`, copy it to a new pathname in the same directory,
   and open that copy through Pencil. Verify three lanes, seven image fills, and
   no clipping before deleting the verification copy.
5. Export and review the fixed image before merge.

Never edit Design or Delivery status only inside Pen. Never commit account
sessions, OTPs, API keys, or local Codex/Pen configuration.

## Pen 1.2.5 checkpoint observations

The First map exposed two local-runtime costs that future Core work must retain
as experiment evidence:

- Flat MCP `Insert` operations created valid nodes with schema and bounds, but
  those nodes did not render. A single nested tree inserted as one top-level
  frame rendered correctly and is the construction seam used by the committed
  atlas. Stable repository IDs remain in card text and normalized input rather
  than depending on Pen-generated IDs.
- The MCP surface has no Save As operation. An initial opaque copy of the
  managed file was a false positive because the visible canvas was still an
  unsaved editor session; a byte-identical repository copy reopened as the
  welcome document and relative screenshots did not resolve from the managed
  directory. The final atlas was rebuilt directly in the repository document,
  saved by the owner, and reopened from a new pathname in the same directory.
  That fresh-open proof found three lanes, seven resolved image fills, and zero
  clipping problems.

These are bounded Core-experiment observations, not adoption conclusions. The
headless CLI remains outside #95; a fresh direct open of the committed file is
now required review evidence.
