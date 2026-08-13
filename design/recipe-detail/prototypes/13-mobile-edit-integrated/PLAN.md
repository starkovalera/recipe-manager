# Integrated Mobile Recipe Edit Prototype Plan

> **Historical execution record:** This completed prototype plan is retained as evidence; its task list is not active backlog.

**Goal:** Create a new isolated interactive mobile Recipe Edit baseline that combines the approved compact shell, top Save action, global navigation, accordion sections, and single-item ingredient editor.

**Architecture:** A static HTML surface uses local mock data and a small vanilla-JavaScript state model. One editor root owns accordion and recipe-draft state; one layer root owns Overflow, Media/Import placeholders, the ingredient editor, and the dirty-exit guard.

**Tech Stack:** Semantic HTML, isolated CSS, vanilla JavaScript, Node Playwright assertions with local Microsoft Edge.

## Global Constraints

- Work only under `design/recipe-detail/`; do not modify production code.
- Keep Prototypes 09–12 unchanged.
- Primary viewport is `390 × 844`; also verify 360 and 430 CSS-pixel widths.
- Preserve approved interactions; do not treat provisional section form details as approved.

---

### Task 1: Integrated mobile shell and accordion

**Files:**
- Create: `index.html`, `styles.css`, `app.js`, `README.md`

**Interfaces:**
- Produces `window.mobileEditPrototype.getState()` for browser assertions.
- Produces one `.mobile-edit-surface`, `.compact-edit-header`, `.global-navigation`, and five `.accordion-section` elements.

- [ ] Create the semantic shell with compact Back/title/Save/Overflow header.
- [ ] Add Basics, Ingredients, Instructions, Cooking notes, and Estimated nutrition as a single-open accordion.
- [ ] Keep global navigation fixed and navigation-only.
- [ ] Add scenario controls outside the product surface.

### Task 2: Approved editor interactions

**Files:**
- Modify: `index.html`, `styles.css`, `app.js`

**Interfaces:**
- Consumes accordion state from Task 1.
- Produces ingredient editor, Overflow sheet, dirty guard, mock save state, and preserved active-section state.

- [ ] Open the approved ingredient editor sheet from the summary row.
- [ ] Support the fixed Unit dictionary through search and six initial chips.
- [ ] Open Overflow with View/Focus/Edit, Media, Import Info, and Delete recipe.
- [ ] Preserve draft and active section when an auxiliary placeholder opens and closes.
- [ ] Invoke the dirty guard from Back; mock Save clears dirty state.

### Task 3: Browser verification and evidence

**Files:**
- Create: `test_prototype.js`, `capture_screenshots.js`
- Create evidence under `design/recipe-detail/screenshots/edit-mode/`.

**Interfaces:**
- Consumes `window.mobileEditPrototype.getState()` and stable data attributes.
- Produces deterministic pass marker `MOBILE_EDIT_INTEGRATED_CHECKS_PASS`.

- [ ] Verify 360, 390, and 430 widths without horizontal overflow.
- [ ] Verify single-open accordion behavior, Save placement, navigation, ingredient sheet, Overflow, and dirty guard.
- [ ] Capture baseline, ingredient-sheet, and Overflow screenshots at 390 × 844.
