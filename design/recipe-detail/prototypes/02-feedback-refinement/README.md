# Recipe Detail Feedback-Refinement Prototype

Status: Browser-evaluated; proposed for user approval  
Updated: 2026-07-22

This is an isolated, dependency-free, low-fidelity prototype. It uses mock data and has no connection to production components, APIs, routes, or styles.

## Start

From the repository root, run:

```powershell
$runtimeRoot='C:\Users\stark\.cache\codex-runtimes\codex-primary-runtime\dependencies'
& "$runtimeRoot\node\bin\node.exe" design\recipe-detail\prototypes\02-feedback-refinement\test_prototype.js
```

The browser runner starts a temporary local server on `127.0.0.1:4174`, evaluates the prototype, writes screenshots, and stops the server. No package download is required.

For manual evaluation, serve this directory with any local static server and open `index.html` through that server.

## Evaluation controls

The toolbar switches:

- realistic sparse, flagged, manual, dense, long, loading, failed, and missing-data scenarios;
- View, Focus, and Edit contexts;
- actions under the title or in a vertical stack beneath the cover;
- ordinary-user and debug-eligible roles.

The prototype evaluates structure and behavior only. Typography, color, spacing, borders, iconography, and imagery are not a high-fidelity direction.

## What changed in v2

- compact import-review status instead of a full-width banner;
- separate source identity and cooking-facts rows;
- bounded Ingredients, Instructions, and Notes with disclosure controls;
- simplified Focus without checkboxes or portion scaling;
- direct View / Focus / Edit navigation in every context;
- Import Info as a responsive drawer or bottom sheet;
- general flags with one `Mark all reviewed` action;
- primary resources grouped with their derived resources;
- cascade-removal confirmation with counts and a current-cover exception.

## Evidence

- screenshots: `design/recipe-detail/screenshots/02-feedback-refinement/`;
- reviews: `design/recipe-detail/reviews/02-feedback-refinement/`;
- browser checks: `test_prototype.js`.
