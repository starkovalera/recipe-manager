# Recipe Detail Structure-Validation Prototype Implementation Plan

> **For agentic workers:** Execute inline in the current worktree. Do not delegate, commit, switch branches, or modify production files.

**Goal:** Build an isolated low-fidelity browser prototype that validates the approved Recipe Detail structure, U1 review behavior, U2 metadata order, responsive layouts, realistic stress data, and Cooking Focus media behavior before high fidelity.

**Architecture:** A dependency-free static prototype uses `index.html` as the semantic shell, `data.js` for mock scenarios, `app.js` for deterministic view/state transitions, and `styles.css` for prototype-only responsive layout. A Python Playwright script starts against a local static server, exercises state selectors and overlays, checks accessibility-relevant DOM behavior, and captures agreed desktop, tablet, and mobile screenshots.

**Tech Stack:** Semantic HTML, prototype-specific CSS, vanilla JavaScript, mock data, Python Playwright.

## Global Constraints

- Work only under `design/recipe-detail/`, except synchronizing the existing authoritative `docs/ui-ux/07-decisions-log.md`.
- Do not modify `frontend/src`, backend code, APIs, schemas, database models, production CSS, production tests, routes, or deployment configuration.
- Do not use production components, application APIs, or the current frontend appearance.
- Use mock data only and no image generation.
- Preserve approved U1: flagged recipes open Default View with a concise status linking to Import Info.
- Preserve approved U2/B2 order: Difficulty / Personal rating, Collections, Tags.
- Keep `Import info` neutral and free of warning icons.
- Do not commit or modify Git refs.

---

### Task 1: Static prototype foundation and scenario model

**Files:**
- Create: `design/recipe-detail/prototypes/01-structure-validation/index.html`
- Create: `design/recipe-detail/prototypes/01-structure-validation/styles.css`
- Create: `design/recipe-detail/prototypes/01-structure-validation/data.js`
- Create: `design/recipe-detail/prototypes/01-structure-validation/README.md`

**Interfaces:**
- `window.prototypeScenarios`: object keyed by `normal`, `flagged`, `manual`, `dense`, `long`, `loading`, `failed`, and `missing`.
- Each usable scenario exposes `recipe`, `importInfo`, and `media` records with realistic strings and arrays.
- The HTML exposes `#scenario-select`, `#view-select`, `#role-select`, `#prototype-root`, and `#live-region`.

- [x] Create a semantic prototype shell with a clearly marked evaluation toolbar and main rendering root.
- [x] Add realistic scenario data, including 50 Tags, 20 Collections, 48 ingredients, 38 steps, long notes, variable nutrition, multiple resource lifecycle states, and eligible debug information.
- [x] Add a restrained grayscale structural stylesheet with desktop, tablet, and mobile breakpoints; avoid production styling and decorative recipe-blog treatment.
- [x] Add startup instructions using `python -m http.server 4173` from the prototype directory.
- [x] Verify `index.html`, `styles.css`, and `data.js` load without external dependencies.

### Task 2: Default View, disclosure, and error-state interactions

**Files:**
- Create: `design/recipe-detail/prototypes/01-structure-validation/app.js`
- Modify: `design/recipe-detail/prototypes/01-structure-validation/index.html`
- Modify: `design/recipe-detail/prototypes/01-structure-validation/styles.css`

**Interfaces:**
- `renderCurrentState()` reads toolbar state and renders one task context.
- `renderDefaultView(scenario)` preserves approved header/content hierarchy.
- `openDisclosure(kind)` and `closeLayer()` manage Tags/Collections popover or mobile sheet.
- `navigateTo(view)` changes task context without a full reload.

- [x] Render title, compact cover treatment, inline source/author/time/servings, approved B2 metadata order, actions, and asymmetric Ingredients/Instructions content.
- [x] Show the concise review status only for flagged scenarios, before recipe content, with a link to Import Info.
- [x] Omit Import Info for manual recipes and keep it neutral for imported recipes.
- [x] Implement fixed visible Tags and Collections with named `+N` disclosure controls and deterministic focus return.
- [x] Render loading, failed-load, and missing-recipe states in the main task context.
- [x] Preserve a stored Default View scroll position when visiting and returning from Import Info.

### Task 3: Import Info and Cooking Focus task contexts

**Files:**
- Modify: `design/recipe-detail/prototypes/01-structure-validation/app.js`
- Modify: `design/recipe-detail/prototypes/01-structure-validation/styles.css`

**Interfaces:**
- `renderImportInfo(scenario)` creates desktop result/evidence split and mobile sequential panels.
- `renderCookingFocus(scenario)` owns temporary ingredient/step checks and active mobile tab.
- `openMedia()` and `closeLayer()` control a desktop nonmodal drawer or mobile bottom sheet without clearing parent cooking state.

- [x] Render Import Info with extracted result and user-meaningful evidence groups: review needed, used, ignored, deleted/restorable, and eligible debug detail.
- [x] Hide debug detail unless the toolbar role is `debug`.
- [x] Render Cooking Focus without organization, provenance, administrative metadata, or a large cover.
- [x] Implement portion scaling, temporary ingredient checks, temporary step completion, and mobile Ingredients/Instructions switching.
- [x] Implement optional media as a right drawer on desktop and bottom sheet on mobile with explicit close/expand controls.
- [x] Keep checks, completed steps, active mobile tab, and scroll position when media opens or closes.
- [x] Render unavailable-media and failed-resource-action feedback in the relevant context.

### Task 4: Automated browser evaluation and screenshots

**Files:**
- Create: `design/recipe-detail/prototypes/01-structure-validation/test_prototype.js`
- Create outputs under: `design/recipe-detail/screenshots/01-structure-validation/`

**Interfaces:**
- The Playwright script reads `PROTOTYPE_URL`, defaulting to `http://127.0.0.1:4173`.
- It exits nonzero on a failed assertion or browser console error.

- [x] Run `python scripts/with_server.py --help` before using the helper.
- [x] Use the locally bundled Node Playwright package because the bundled Python runtime does not contain the Python Playwright module; do not download dependencies.
- [x] Write assertions for normal, flagged, manual, dense, long, failed, and missing states.
- [x] Assert flagged status navigation, manual Import Info omission, approved metadata DOM order, and disclosure focus return.
- [x] Assert Cooking Focus state survives media open/close and mobile tab switching.
- [x] Capture `1440 × 900`, `1024 × 768`, and `390 × 844` screenshots for required states.
- [x] Attempt the helper-managed server first; if the bundled Python server accepts a socket but returns an empty HTTP response, use the test runner's dependency-free Node `http` fallback and document the runtime limitation.
- [x] Run the browser test and confirm zero assertion failures and zero uncaught console errors.

### Task 5: Separate critique and approval gate

**Files:**
- Create: `design/recipe-detail/reviews/01-structure-validation/ux-review.md`
- Create: `design/recipe-detail/reviews/01-structure-validation/visual-review.md`
- Create: `design/recipe-detail/reviews/01-structure-validation/product-fit-review.md`
- Create: `design/recipe-detail/reviews/01-structure-validation/accessibility-review.md`
- Create: `design/recipe-detail/reviews/01-structure-validation/responsive-long-content-review.md`

**Interfaces:**
- Every review records evidence, pass/fail findings, limitations, and required next changes.

- [x] Review one-primary-task clarity, context transitions, disclosure, and state recovery.
- [x] Review hierarchy, density, card avoidance, metadata competition, and prototype-only visual limitations.
- [x] Review imported/manual behavior, Import Info separation, Cooking Focus simplification, and role visibility.
- [x] Review keyboard order, focus return, text alternatives, non-color status, layer semantics, and touch targets.
- [x] Review desktop/tablet/mobile overflow, long title, 50 Tags, 20 Collections, 48 ingredients, 38 steps, drawer/sheet behavior, and scroll preservation.
- [x] Mark the prototype as proposed for user approval and explicitly retain the high-fidelity gate.

## Self-review

- Coverage: all S1–S12 scenario families are represented directly or through a selectable combined stress state.
- Boundaries: every new executable or visual file stays under `design/recipe-detail/`; the only other modification is the authoritative decisions log.
- Placeholders: the plan contains no TODO/TBD content and requires realistic mock data.
- Consistency: U1 and U2/B2 are fixed across all prototype tasks.
- Git: no commit step is included because the user prohibited commits and Git-ref changes.
