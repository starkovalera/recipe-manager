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
4. Export and review the fixed image before merge.

Never edit Design or Delivery status only inside Pen. Never commit account
sessions, OTPs, API keys, or local Codex/Pen configuration.

## Pen 1.2.5 checkpoint observations

The First map exposed two local-runtime costs that future Core work must retain
as experiment evidence:

- MCP `Insert` operations created valid nodes with schema and bounds, but the
  new nodes did not render. Copying the already-visible smoke primitive and
  applying bounded overrides rendered correctly. The committed atlas therefore
  uses copied visible primitives; stable repository IDs live in node metadata
  and the normalized input, not in Pen-generated IDs.
- The current MCP surface has no Save As operation. The agent preserved the
  managed source, copied the opaque `.pen` file without parsing it, and then
  retained only the derived atlas in the repository copy. Screenshot fills use
  repository-relative paths in the committed `.pen`; the fixed review export
  was captured from the same atlas with temporary absolute local paths because
  the active managed document did not rebase relative assets until the
  repository file is opened directly.

These are bounded Core-experiment observations, not adoption conclusions. The
headless CLI and a fresh direct open of the committed file remain outside #95.
