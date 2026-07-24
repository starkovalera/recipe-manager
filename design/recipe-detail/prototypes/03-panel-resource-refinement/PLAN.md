# Recipe Detail v3 Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Subagents are intentionally unavailable for this run.

**Goal:** Build a separate low-fidelity v3 prototype comparing header variants A/B and validating image previews, local cascade confirmation, and one shared Media/Import Info panel slot.

**Architecture:** Preserve v2 unchanged and copy its dependency-free mock prototype into `03-panel-resource-refinement`. Extend the existing single-layer state rather than introducing nested dialogs. Keep all data local and all visual evidence under the Recipe Detail design tree.

**Tech Stack:** Static HTML/CSS/JavaScript, local SVG assets, Node HTTP server, Playwright with bundled Edge.

## Global constraints

- Do not modify production code, production CSS, backend, APIs, schemas, routes, or production tests.
- Keep executable artifacts under `design/recipe-detail/prototypes/03-panel-resource-refinement/`.
- Keep v1 and v2 unchanged.
- Use mock data only; do not use image generation.
- Do not commit or modify Git refs.

### Task 1: Isolated v3 and header comparison

**Files:** Copy v2 prototype files; modify v3 `index.html`, `styles.css`, `app.js`, `README.md`, and `test_prototype.js`.

- [x] Copy dependency-free v2 source files into the v3 directory without copying v2 screenshots.
- [x] Rename labels, server port, screenshot paths, and test output for v3.
- [x] Replace the vertical under-cover variant with corrected B: one horizontal row spanning from the cover edge below the top header row.
- [x] Add browser assertions that A starts at the title edge while B starts at the cover edge and remains horizontal.

### Task 2: Image previews and local cascade confirmation

**Files:** Modify v3 `data.js`, `app.js`, `styles.css`; create local SVG files under `assets/`; extend `test_prototype.js`.

- [x] Add distinct local thumbnail assets and preview metadata only to image resources.
- [x] Render image thumbnails and accessible inline expand/collapse controls.
- [x] Move primary-resource confirmation inside its resource group, between the primary row and its children.
- [x] Mark affected child rows while leaving the current cover protected; focus Cancel and support Escape.
- [x] Verify the confirmation is spatially adjacent to the selected group and is cancelled by leaving Import Info.

### Task 3: Shared Media / Import Info slot

**Files:** Modify v3 `app.js`, `styles.css`, and `test_prototype.js`.

- [x] Add a context switch inside the open panel whenever both Media and Import Info are available.
- [x] Switch the existing layer in place without stacking dialogs.
- [x] Preserve Media selection, expansion, and per-panel scroll while switching.
- [x] Cancel pending destructive confirmation on panel switch.
- [x] Verify the same state model on desktop, 1024 px tablet, and 390 px mobile.

### Task 4: Evidence and critiques

**Files:** Create screenshots under `design/recipe-detail/screenshots/03-panel-resource-refinement/` and reviews under `design/recipe-detail/reviews/03-panel-resource-refinement/`.

- [x] Capture A, corrected B, image hierarchy, inline confirmation, Focus Media, Focus Import Info, tablet switching, and mobile sheet switching.
- [x] Run clean-console, focus, overflow, dimensions, and server-lifecycle checks.
- [x] Write separate UX, visual, product-fit, accessibility, and responsive reviews.
- [x] Update the decision log with approved interaction rules while keeping the A/B choice open.
