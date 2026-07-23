# Recipe Detail v4 Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Subagents are intentionally unavailable for this run.

**Goal:** Produce a separate v4 low-fidelity prototype that keeps A/B comparable, clarifies image/resource controls and deletion consequences, and simplifies the shared auxiliary drawer around the common Media task.

**Architecture:** Copy v3 without changing it, then make targeted rendering, state, mock-data, CSS, and Playwright changes in `04-visual-control-refinement`. Keep one auxiliary layer but replace persistent tabs with a contextual Media overflow transition and conditional Back action.

**Tech Stack:** Static HTML/CSS/JavaScript, local SVG thumbnails and icons, Node HTTP server, Playwright with bundled Edge.

## Global constraints

- No production frontend, backend, API, schema, route, production CSS, or production-test changes.
- All executable changes remain under `design/recipe-detail/prototypes/04-visual-control-refinement/`.
- Preserve v1–v3 unchanged.
- Mock data only; no image generation.
- No Git commits, branch changes, or ref mutations.

### Task 1 — Isolated v4 and fair header comparison

- [x] Copy v3 source/assets into v4 and update labels, port 4176, screenshot paths, and README.
- [x] Make review-status width 620 px in both A and corrected B while retaining their distinct left alignment.
- [x] Test normal, flagged, long-title/no-cover, and mobile comparison geometry.

### Task 2 — Resource icons, alignment, and deletion copy

- [x] Replace preview-close text with an accessible corner cross icon and resource-delete crosses with trash icons.
- [x] Use a stable resource-row grid so every consequence label occupies the same right column.
- [x] Add explicit saved-recipe invariance copy to cascade confirmation and retain count/type/cover information.
- [x] Test accessible names, hit targets, focus, Escape cancellation, and spatial adjacency.

### Task 3 — Equal-width contextual auxiliary drawer

- [x] Remove Media Compact/Expand and the persistent two-tab switcher.
- [x] Keep Media and Import Info at identical widths for each breakpoint.
- [x] Add a Media overflow menu with `Import info`; replace the panel in place and show conditional `Back to media`.
- [x] Preserve Media selection/scroll and Cooking Focus position; cancel unconfirmed destructive state on replacement.
- [x] Test direct Import Info, contextual return, close behavior, modal semantics, and one-dialog invariant.

### Task 4 — Images and external cooking links

- [x] Add realistic mock video/link records distinct from image media.
- [x] Render `Images` and `Videos & links` sections with descriptive external actions and platform/author context.
- [x] Test link semantics, external-link attributes, long labels, and mobile overflow.

### Task 5 — Evidence and decision records

- [x] Capture A/B flagged, long-title A/B, resource controls, cascade copy, Media images/links, contextual Import Info, tablet, and mobile.
- [x] Run browser, dimensions, console, focus, overflow, server-lifecycle, and production-boundary checks.
- [x] Write separate UX, visual, product-fit, accessibility, and responsive reviews.
- [x] Update the decisions log while keeping final A/B selection open.
