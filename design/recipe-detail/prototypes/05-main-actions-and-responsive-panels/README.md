# Recipe Detail Main Actions and Responsive Panels Prototype

Status: approved low-fidelity desktop behavior foundation
Updated: 2026-07-23

This isolated low-fidelity v5 prototype uses local mock data and SVG assets. It has no dependency on production components, APIs, routes, or styles.

## Evaluation focus

- approved corrected-B action placement;
- separate mode and resource action groups;
- persistent conditional `Media · N` in View, Focus, and Edit;
- equal-width, single-slot Media and Import Info panels without internal cross-navigation;
- overlay behavior on 1280 px and 1024 px desktop widths;
- mobile two-row actions and swipe-down sheet dismissal with a retained cross;
- uniform trash controls and cross close controls;
- conditional Ignored resources grouped by primary source.
- inline irreversible-removal confirmation for every secondary resource, including ignored images.
- overflow-based irreversible recipe deletion with desktop dialog, mobile sheet, success destination, and retryable failure state.
- desktop Import Info under Overflow, with matching pending-review dots on Overflow and its menu item; no permanent desktop Import Info button.
- first-entry automatic Import Info opening for flagged imported recipes, once per recipe visit without reopening on View/Focus/Edit changes.

Prototype 05 remains authoritative for desktop panel/resource behavior. Its older mobile action-row captures are historical responsive evidence; current mobile header, Overflow, Import Info, and global-navigation behavior is defined by Prototypes 06 and 10 and decisions 08, 10, and 11.

## Run

```powershell
$runtimeRoot='C:\Users\stark\.cache\codex-runtimes\codex-primary-runtime\dependencies'
$pnpm="$runtimeRoot\node\node_modules\.pnpm"
$env:NODE_PATH="$pnpm\playwright@1.61.1\node_modules;$pnpm\playwright-core@1.61.1\node_modules"
& "$runtimeRoot\node\bin\node.exe" design\recipe-detail\prototypes\05-main-actions-and-responsive-panels\test_prototype.js
```

Evidence is under `design/recipe-detail/screenshots/05-main-actions-and-responsive-panels/` and `design/recipe-detail/reviews/05-main-actions-and-responsive-panels/`.
