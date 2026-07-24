# Recipe Detail Feedback-Refinement Prototype Plan

Status: Executed; awaiting design approval  
Updated: 2026-07-22

**Goal:** Create a separate v2 low-fidelity prototype that applies the user's review of Default View, Focus, and Import Info while preserving v1 for comparison.

**Architecture:** Copy the verified dependency-free v1 prototype into a new isolated directory, then revise mock data, semantic rendering, responsive CSS, and Playwright coverage. A toolbar-only `Action placement` control compares under-title versus under-cover actions without changing any other header variable.

## Constraints

- New executable artifacts remain under `design/recipe-detail/prototypes/02-feedback-refinement/`.
- Do not modify production frontend, backend, APIs, schemas, tests, styles, routes, or deployment configuration.
- Inspect backend only for functional behavior; never use current frontend visuals.
- Use mock data only and no image generation.
- Preserve v1 unchanged.
- Do not commit or modify Git refs.

## Task 1 — Isolated v2 foundation

- [x] Copy v1 HTML, CSS, data, JavaScript, README, and browser-test files into the new v2 directory.
- [x] Update titles, artifact labels, startup instructions, output paths, and test names for v2.
- [x] Keep the prototype dependency-free and preserve the verified local Node HTTP test runner.

## Task 2 — Default View refinement

- [x] Replace the full-width review strip with a compact status block aligned to the primary identity/content region.
- [x] Split source identity from cooking facts into two separate rows.
- [x] Add a toolbar comparison between actions under the title and a vertical action stack under the cover.
- [x] Add a persistent `View · Focus · Edit` mode switch and keep Import Info as a separate drawer action.
- [x] Collapse Ingredients after 12 items, Instructions after 8 steps, and Notes after 4 lines, with accessible expand/collapse controls and focus return.

## Task 3 — Simplified Focus

- [x] Remove ingredient checkboxes, completed-step controls, and portion scaling.
- [x] Keep the same `View · Focus · Edit` switch and Import Info action.
- [x] Retain mobile Ingredients/Instructions switching and optional media drawer/sheet.

## Task 4 — Import Info resource drawer

- [x] Open Import Info over or beside the current View/Focus context rather than replacing it.
- [x] Remove Extracted Result, Provenance, and Original source.
- [x] Show all open flags as general messages with one `Mark all reviewed` action.
- [x] Explain that marking reviewed changes flags only, not recipe content or resources.
- [x] Group derived resources beneath each primary resource using indentation and a connector rather than nested cards.
- [x] Show type/status/count summaries, individual derived removal, and current-cover protection.
- [x] Confirm primary URL deletion with counts by derived type and state that current cover remains.
- [x] Show a collapsed removed-resource type summary only when removed resources exist; do not offer Restore.
- [x] Keep `Extraction details` role-gated for debug users.

## Task 5 — Responsive behavior

- [x] Wide desktop: drawer reallocates width and leaves the underlying context visible.
- [x] Tablet: drawer overlays the context without narrowing it.
- [x] Mobile: drawer becomes a modal bottom sheet with inert background and focus trap.
- [x] Preserve context, scroll position, expanded sections, and active mobile Focus tab when drawers close.

## Task 6 — Browser evaluation and approval evidence

- [x] Test both action-placement variants with identical recipe data.
- [x] Test compact flagged status, content expansion, bulk flag review, resource hierarchy, individual removal, cascade confirmation, removed summary, and cover exception.
- [x] Test View/Focus/Edit navigation availability in Default and Focus.
- [x] Capture desktop header variants, desktop resource drawer, tablet overlay drawer, mobile resource sheet, mobile Focus, and long-content expansion.
- [x] Verify exact viewport sizes, no horizontal overflow, clean console, and no orphan localhost server.
- [x] Write focused UX, visual, product-fit, accessibility, and responsive critiques.

## Approval gate

- [ ] User chooses the header-action placement.
- [ ] User approves or revises the resource grouping.

## Self-review

- No production implementation is included.
- Flags remain general messages and are cleared only in bulk.
- Resource hierarchy and cascade behavior match the inspected backend model.
- Deleted-resource restoration is not represented.
- The accepted 1024 px responsive rule is fixed rather than reopened.
