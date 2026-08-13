# Recipe Detail Panel-and-Resource Refinement Prototype

Status: Browser-evaluated; proposed for user approval  
Updated: 2026-07-23

This isolated low-fidelity v3 prototype uses local mock data and SVG thumbnails. It has no dependency on production components, APIs, routes, or styles.

## Run the evaluation

From the repository root:

```powershell
$runtimeRoot='C:\Users\stark\.cache\codex-runtimes\codex-primary-runtime\dependencies'
$pnpm="$runtimeRoot\node\node_modules\.pnpm"
$env:NODE_PATH="$pnpm\playwright@1.61.1\node_modules;$pnpm\playwright-core@1.61.1\node_modules"
& "$runtimeRoot\node\bin\node.exe" design\recipe-detail\prototypes\03-panel-resource-refinement\test_prototype.js
```

The test starts a temporary server on `127.0.0.1:4175`, writes screenshots, and stops the server.

## Evaluation controls

- Action placement compares A under the title with corrected B beginning at the cover edge.
- Context switches Default View, Cooking Focus, and the Edit placeholder.
- Import Info image thumbnails expand inline.
- Primary resource removal expands confirmation inside its group.
- Cooking Focus uses one auxiliary slot whose content switches between Media and Import Info.

This is not a high-fidelity visual direction. Local SVGs exist only to make resource identity and deletion consequences testable.

## Evidence

- screenshots: `design/recipe-detail/screenshots/03-panel-resource-refinement/`;
- reviews: `design/recipe-detail/reviews/03-panel-resource-refinement/`;
- approved interaction spec: `design/recipe-detail/decisions/03-panel-resource-refinement.md`.
