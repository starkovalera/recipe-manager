# Recipe Detail Visual-Control Refinement Prototype

Status: Browser-evaluated; proposed for user approval  
Updated: 2026-07-23

This isolated low-fidelity v4 prototype uses local mock data and SVG assets. It does not use production components, APIs, routes, or styles.

## Run

From the repository root:

```powershell
$runtimeRoot='C:\Users\stark\.cache\codex-runtimes\codex-primary-runtime\dependencies'
$pnpm="$runtimeRoot\node\node_modules\.pnpm"
$env:NODE_PATH="$pnpm\playwright@1.61.1\node_modules;$pnpm\playwright-core@1.61.1\node_modules"
& "$runtimeRoot\node\bin\node.exe" design\recipe-detail\prototypes\04-visual-control-refinement\test_prototype.js
```

The runner starts a temporary server on `127.0.0.1:4176`, captures screenshots, and stops the server.

## Evaluation focus

- fair A/B header comparison with identical compact warning width;
- distinct close-preview and remove-resource icons;
- stable cascade consequence column and explicit saved-recipe invariance;
- equal-width Media and Import Info drawers without Compact/Expand;
- rare Media → Import Info transition through overflow and contextual Back;
- Media sections for images and external cooking links.

## Evidence

- screenshots: `design/recipe-detail/screenshots/04-visual-control-refinement/`;
- reviews: `design/recipe-detail/reviews/04-visual-control-refinement/`;
- approved spec: `design/recipe-detail/decisions/04-visual-control-refinement.md`.
