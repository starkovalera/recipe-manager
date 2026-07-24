# Mobile Global Navigation Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an isolated mobile prototype iteration that validates the approved global bottom bar and its interaction with Recipe Detail modal sheets.

**Architecture:** Copy Prototype 06 into Prototype 10 as a frozen Recipe Detail baseline, then add one application-shell navigation component and extend the existing single `layer-root` modal slot. All data remains local mock data; no production components or APIs are used.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript, Node.js, Playwright, local SVG assets.

**Execution status:** Completed and verified on 2026-07-24. No commit or publication was performed in this pass.

## Global Constraints

- Modify only design artifacts under `design/recipe-detail/`.
- Do not change Prototype 06 or production application files.
- Preserve all approved Recipe Detail behavior.
- The global bar has Recipes, Collections, Notifications, and Profile destinations plus a distinct central Add action.
- Every modal sheet covers and disables the global bar; sheets replace rather than stack.
- Administration is available from Profile only for the admin role.
- Do not commit or publish during this execution pass.

---

### Task 1: Freeze the baseline and specify the shell

**Files:**
- Create: `design/recipe-detail/prototypes/10-mobile-global-navigation/` from Prototype 06
- Create: `design/recipe-detail/prototypes/10-mobile-global-navigation/README.md`

- [ ] Copy Prototype 06 without modifying the source iteration.
- [ ] Update the new prototype title and README to name the global-navigation evaluation scope.

### Task 2: Test the approved navigation and modal layering

**Files:**
- Modify: `design/recipe-detail/prototypes/10-mobile-global-navigation/test_prototype.js`

- [ ] Add assertions for four labeled destinations, a distinct Add recipe control, current Recipes state, admin placement, minimum touch targets, and content bottom clearance.
- [ ] Add assertions that Add, Media, Overflow, Import Info, and deletion sheets cover the global bar and that only one dialog exists.
- [ ] Run the Playwright suite and verify the new assertions fail because the global bar is absent.

### Task 3: Implement the minimal interactive shell

**Files:**
- Modify: `design/recipe-detail/prototypes/10-mobile-global-navigation/index.html`
- Modify: `design/recipe-detail/prototypes/10-mobile-global-navigation/app.js`
- Modify: `design/recipe-detail/prototypes/10-mobile-global-navigation/styles.css`

- [ ] Render the fixed application bar outside Recipe Detail content and below the single modal layer.
- [ ] Implement the Add chooser with Import recipe and Create manually actions.
- [ ] Add mock destination surfaces and expose Administration only through admin Profile.
- [ ] Preserve page state when a modal sheet opens or closes.
- [ ] Run the full suite until all assertions pass.

### Task 4: Review and evidence

**Files:**
- Create: `design/recipe-detail/screenshots/10-mobile-global-navigation/`
- Create: `design/recipe-detail/reviews/10-mobile-global-navigation/ux-review.md`

- [ ] Capture 390 x 844 screenshots for ordinary Recipe Detail, Add chooser, Media, Overflow, Import Info, and admin Profile.
- [ ] Record UX, accessibility, responsive, and product-fit findings and remaining visual questions.
- [ ] Run the full Prototype 10 test suite and verify a stable final pass marker.
