# Mobile Recipe Detail Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete isolated mobile-first Recipe Detail prototype covering Default View, Cooking Focus, Media, Import Info, metadata disclosure, and destructive recipe actions while Edit Mode remains a visible non-functional entry.

**Architecture:** A static HTML shell loads local mock scenarios from `data.js` and renders all product states through a small state machine in `app.js`. One page root owns View/Focus state; one layer root owns exactly one bottom sheet or blocking confirmation. Prototype evaluation controls remain outside the simulated product surface.

**Tech Stack:** Semantic HTML, standalone CSS, vanilla JavaScript, local SVG assets, Node Playwright browser assertions.

## Global Constraints

- Work only under `design/recipe-detail/`; do not modify production code, APIs, schemas, tests, routing, or production CSS.
- The prototype must have no runtime dependency on Prototype 05 or production components.
- Use local mock data and local assets only; do not use image generation.
- Primary viewport: `390 × 844`; also verify 360 px and 430 px widths.
- Default View is a sequential reading page; only Cooking Focus switches Ingredients and Instructions.
- `Edit` remains visible and announces `Edit Mode is being designed.` without changing context.
- Media and Import Info use one equal-width sheet slot, have no internal cross-navigation, and never stack.
- Media and Import Info support cross and swipe-down dismissal; destructive recipe deletion does not support swipe dismissal.
- No ingredient/step checkboxes, portion scaling, embedded video, or functional Edit Mode.
- Keep historical prototypes and screenshots; create new artifact names rather than overwriting approved evidence.

---

## File map

- Create `design/recipe-detail/prototypes/06-mobile-recipe-detail/index.html`: evaluation toolbar, product root, layer root, and live region.
- Create `design/recipe-detail/prototypes/06-mobile-recipe-detail/styles.css`: mobile visual system, sequential reading layout, sheets, dialogs, responsive bounds, focus, and reduced motion.
- Create `design/recipe-detail/prototypes/06-mobile-recipe-detail/data.js`: immutable mock scenarios, media, import-resource hierarchy, and state labels.
- Create `design/recipe-detail/prototypes/06-mobile-recipe-detail/app.js`: state machine, render functions, event delegation, focus management, swipe dismissal, and mock mutations.
- Create `design/recipe-detail/prototypes/06-mobile-recipe-detail/test_prototype.js`: deterministic Playwright verification at 360, 390, and 430 px.
- Create `design/recipe-detail/prototypes/06-mobile-recipe-detail/README.md`: scope, controls, run command, and evidence paths.
- Create local SVG copies under `design/recipe-detail/prototypes/06-mobile-recipe-detail/assets/` for the cover and media thumbnails.
- Create screenshots under `design/recipe-detail/screenshots/06-mobile-recipe-detail/`.
- Create five critique files under `design/recipe-detail/reviews/06-mobile-recipe-detail/`.
- Modify `design/recipe-detail/prototypes/00-decision-gallery/index.html` only after the mobile prototype is approved.

---

### Task 1: Independent shell, mock data, and smoke test

**Files:**
- Create: `design/recipe-detail/prototypes/06-mobile-recipe-detail/index.html`
- Create: `design/recipe-detail/prototypes/06-mobile-recipe-detail/data.js`
- Create: `design/recipe-detail/prototypes/06-mobile-recipe-detail/styles.css`
- Create: `design/recipe-detail/prototypes/06-mobile-recipe-detail/app.js`
- Create: `design/recipe-detail/prototypes/06-mobile-recipe-detail/test_prototype.js`
- Create: `design/recipe-detail/prototypes/06-mobile-recipe-detail/README.md`
- Copy as new files: `design/recipe-detail/prototypes/06-mobile-recipe-detail/assets/*.svg`

**Interfaces:**
- Produces: `window.mobileRecipeScenarios: Record<string, Scenario>`.
- Produces: `window.mobileRecipePrototype.getState(): PrototypeState` for browser assertions.
- Produces: DOM roots `#prototype-root`, `#layer-root`, and `#live-region`.

- [ ] **Step 1: Write the failing smoke assertions**

Create `test_prototype.js` with a static-server helper and these first assertions:

```js
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

async function smoke(page, baseUrl) {
  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await page.locator('#prototype-root [data-product-surface]').waitFor();
  assert.equal(await page.locator('#scenario-select option').count(), 9);
  assert.equal(await page.locator('#layer-root').getAttribute('aria-live'), null);
  assert.equal(await page.locator('#live-region').getAttribute('aria-live'), 'polite');
}
```

- [ ] **Step 2: Run the test and verify the shell is absent**

Run the completed test harness using the bundled Node/Playwright paths documented in Prototype 05.

Expected: FAIL because `index.html` and `#prototype-root` do not exist.

- [ ] **Step 3: Create the semantic shell**

`index.html` must contain this stable contract:

```html
<header class="prototype-toolbar">
  <label>Scenario <select id="scenario-select"></select></label>
  <label>Context <select id="context-select"><option value="default">View</option><option value="focus">Focus</option></select></label>
  <label>Role <select id="role-select"><option value="user">User</option><option value="debug">Debug</option></select></label>
  <label>Delete result <select id="delete-result-select"><option value="success">Success</option><option value="failure">Failure</option></select></label>
</header>
<main id="prototype-root"></main>
<div id="layer-root"></div>
<div id="live-region" class="sr-only" aria-live="polite" aria-atomic="true"></div>
```

- [ ] **Step 4: Define the data contract and all nine scenarios**

`data.js` must expose records with this shape:

```js
window.mobileRecipeScenarios = {
  normal: { state: 'ready', recipe: {}, media: [], mediaLinks: [], importInfo: {} },
  flagged: { state: 'ready', recipe: {}, media: [], mediaLinks: [], importInfo: {} },
  manual: { state: 'ready', recipe: {}, media: [], mediaLinks: [], importInfo: null },
  noCover: { state: 'ready', recipe: {}, media: [], mediaLinks: [], importInfo: {} },
  dense: { state: 'ready', recipe: {}, media: [], mediaLinks: [], importInfo: {} },
  long: { state: 'ready', recipe: {}, media: [], mediaLinks: [], importInfo: {} },
  loading: { state: 'loading' },
  failed: { state: 'failed', message: 'The recipe could not be loaded. Your library is still available.' },
  missing: { state: 'missing', message: 'This recipe no longer exists or you do not have access.' }
};
```

Use the realistic Smoky Tomato & Butter Bean Stew content, 50 tags/20 collections in `dense`, and 48 ingredients/38 steps in `long`.

- [ ] **Step 5: Add the minimal state machine and render entry point**

`app.js` begins with this stable state:

```js
const state = {
  scenario: 'normal', context: 'default', role: 'user', deleteResult: 'success',
  layer: null, layerTrigger: null, defaultScroll: 0, focusTab: 'ingredients',
  expanded: { ingredients: false, instructions: false, notes: false },
  selectedMedia: 0, reviewed: new Set(), removedIds: new Set(), removedItems: [],
  pending: null, panelScroll: { media: 0, import: 0 }, sheetGesture: null
};

const prototypeRoot = document.querySelector('#prototype-root');
const layerRoot = document.querySelector('#layer-root');
function currentScenario() { return window.mobileRecipeScenarios[state.scenario]; }
function render() {
  const scenario = currentScenario();
  prototypeRoot.innerHTML = scenario.state === 'ready'
    ? `<article class="product-surface" data-product-surface><p>Recipe surface ready</p></article>`
    : `<section class="product-surface state-panel" data-product-surface><h1>${scenario.state === 'loading' ? 'Loading recipe' : scenario.state === 'missing' ? 'Recipe not found' : 'Recipe failed to load'}</h1></section>`;
  renderLayer();
}
function renderLayer() { layerRoot.replaceChildren(); }
window.mobileRecipePrototype = { getState: () => state };
render();
```

- [ ] **Step 6: Add baseline mobile tokens and containment**

Define explicit tokens and a single product column:

```css
:root { color-scheme: light; --ink:#1f3340; --muted:#617480; --line:#c8d3d9; --canvas:#eaf0f3; --paper:#fff; --blue:#174e6c; --blue-soft:#deebf2; --amber:#fff3cf; --danger:#982f2f; }
* { box-sizing:border-box; }
body { margin:0; background:var(--canvas); color:var(--ink); font-family:Inter, ui-sans-serif, system-ui, sans-serif; }
.product-surface { width:min(100%, 430px); min-height:100vh; margin-inline:auto; overflow:clip; background:var(--paper); }
:focus-visible { outline:3px solid #3d7898; outline-offset:2px; }
```

- [ ] **Step 7: Run the smoke test**

Expected: nine scenarios exist; the product surface loads at 390 px; no console errors.

- [ ] **Step 8: Commit the independent shell**

Commit only Task 1 files with message:

```text
feat(ui-ux): scaffold mobile recipe detail prototype
```

---

### Task 2: Sequential Default View and scenario behavior

**Files:**
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/app.js`
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/styles.css`
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/test_prototype.js`

**Interfaces:**
- Produces: `renderDefault(recipe)`, `renderHeader(recipe)`, `renderMainActions('default')`, `renderMetadata(recipe)`, and `renderExpandableSection()`.
- Consumes: scenario contract and state from Task 1.

- [ ] **Step 1: Add failing assertions for Default View**

Assert all of the following:

```js
await page.selectOption('#scenario-select', 'flagged');
await assertText(page, 'h1', 'Smoky Tomato & Butter Bean Stew');
assert.equal(await page.getByRole('button', { name: 'Import info' }).count(), 1);
assert.equal(await page.locator('.review-status').count(), 1);
assert.equal(await page.locator('.recipe-section[data-section="ingredients"] li').count(), 12);
assert.equal(await page.locator('.recipe-section[data-section="instructions"] li').count(), 8);
await page.selectOption('#scenario-select', 'manual');
assert.equal(await page.getByRole('button', { name: 'Import info' }).count(), 0);
```

- [ ] **Step 2: Run and verify failure**

Expected: FAIL because header, actions, metadata, and sections are not rendered.

- [ ] **Step 3: Implement header and two-row actions**

Use one header grid for cover/title and separate identity/facts rows. Render actions with these data hooks:

```html
<nav class="mode-actions" aria-label="Recipe mode">
  <button data-context="default" aria-current="page">View</button>
  <button data-context="focus">Focus</button>
  <button data-action="edit-status">Edit</button>
</nav>
<div class="resource-actions">
  <button data-action="media">Media · 6</button>
  <button data-action="import">Import info</button>
  <button data-action="overflow" aria-label="More recipe actions">…</button>
</div>
```

- [ ] **Step 4: Implement bounded metadata and review status**

`visibleMetadata(values, limit = 2)` returns two values plus a button with `data-disclosure="tags|collections"` and `+N` text. `reviewStatus()` renders only when the current scenario has unresolved flags and has not been added to `state.reviewed`.

- [ ] **Step 5: Implement sequential reading sections**

`renderExpandableSection({ key, items, threshold, ordered })` must preserve independent state and render `Show all N` / `Show first N`. Render mobile order: Ingredients, Instructions, Estimated Nutrition, Cooking Notes.

- [ ] **Step 6: Implement conditional scenarios and retry actions**

Render loading with `aria-busy="true"`; failed and missing states use `role="alert"`. `Try again` switches failed to normal mock data; `Return to recipes` renders a mock Recipes destination.

- [ ] **Step 7: Run Default View assertions at 360, 390, and 430 px**

Expected: no horizontal overflow; long title wraps; manual scenario omits Import Info; dense metadata exposes `+N`.

- [ ] **Step 8: Commit Default View**

```text
feat(ui-ux): add mobile recipe reading view
```

---

### Task 3: Cooking Focus and state restoration

**Files:**
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/app.js`
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/styles.css`
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/test_prototype.js`

**Interfaces:**
- Produces: `setContext(context)`, `renderFocus(recipe)`, and `state.focusTab`.
- Consumes: `renderMainActions(activeContext)` from Task 2.

- [ ] **Step 1: Add failing Focus assertions**

```js
await page.getByRole('button', { name: 'Focus' }).click();
assert.equal(await page.locator('.recipe-cover').count(), 0);
assert.equal(await page.locator('.secondary-metadata').count(), 0);
assert.equal(await page.locator('.review-status').count(), 0);
assert.equal(await page.getByRole('tab', { name: 'Ingredients' }).getAttribute('aria-selected'), 'true');
assert.equal(await page.locator('input[type="checkbox"]').count(), 0);
assert.equal(await page.getByText(/portion|serving multiplier/i).count(), 0);
```

- [ ] **Step 2: Run and verify failure**

Expected: FAIL because Focus is not implemented.

- [ ] **Step 3: Implement Focus structure**

Render compact title/facts, both main-action rows, and this switch:

```html
<div class="focus-switch" role="tablist" aria-label="Focus section">
  <button role="tab" data-focus-tab="ingredients" aria-selected="true">Ingredients</button>
  <button role="tab" data-focus-tab="instructions" aria-selected="false">Instructions</button>
</div>
```

Ingredients and Instructions are mutually visible. Notes follow Instructions. Do not render cover, source, metadata, review status, nutrition, checkboxes, or a multiplier.

- [ ] **Step 4: Preserve positions and announce unfinished Edit**

Before entering Focus, save `window.scrollY` to `state.defaultScroll`. Returning to View restores it with `requestAnimationFrame`. `data-action="edit-status"` calls `announce('Edit Mode is being designed.')` and leaves `state.context` unchanged.

- [ ] **Step 5: Run Focus and restoration assertions**

Expected: tab switching works, Edit does not navigate, returning View restores scroll within a 2 px tolerance.

- [ ] **Step 6: Commit Focus**

```text
feat(ui-ux): add mobile cooking focus
```

---

### Task 4: Shared bottom-sheet engine, metadata disclosure, and Media

**Files:**
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/app.js`
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/styles.css`
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/test_prototype.js`

**Interfaces:**
- Produces: `openLayer(type, trigger, details)`, `closeLayer()`, `renderLayer()`, `startSheetGesture()`, and `finishSheetGesture()`.
- Produces layer types: `media`, `import`, `disclosure`, `overflow`, `delete-recipe`.

- [ ] **Step 1: Add failing sheet and Media assertions**

Assert dialog naming, focus entry/return, cross close, selected thumbnail, understandable link actions, absence of raw URLs/deletion controls, and preserved Focus tab.

- [ ] **Step 2: Run and verify failure**

Expected: FAIL because no layer engine exists.

- [ ] **Step 3: Implement one-slot sheet rendering**

Every non-destructive mobile sheet uses:

```html
<div class="sheet-backdrop"></div>
<section class="bottom-sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title">
  <div class="sheet-handle" aria-hidden="true"></div>
  <header class="sheet-heading"><h2 id="sheet-title"></h2><button data-action="close-layer" aria-label="Close">…</button></header>
  <div class="sheet-body"></div>
</section>
```

Opening stores the trigger; closing restores focus and saves panel scroll.

- [ ] **Step 4: Implement metadata disclosure sheets**

`+N` opens a compact list of all Tags or Collections. Closing returns to the corresponding disclosure button. It must not expose edit controls.

- [ ] **Step 5: Implement Media content**

Render selected preview, caption/origin/current-cover marker, thumbnail buttons, and external actions labeled `Watch Instagram cooking video` and `Open Marta Cooks post`. Never render raw URLs as the action label.

- [ ] **Step 6: Implement swipe-down dismissal**

Track a pointer gesture only from `.sheet-handle`. Close when downward distance is at least 96 px or velocity is at least 0.65 px/ms. Ignore upward movement and any gesture started inside `.sheet-body`.

- [ ] **Step 7: Run Media, disclosure, and gesture assertions**

Expected: cross, Escape, and swipe close Media; selected thumbnail and scroll survive reopen; no sheet stacking occurs.

- [ ] **Step 8: Commit the sheet engine and Media**

```text
feat(ui-ux): add mobile media and disclosure sheets
```

---

### Task 5: Import Info review and resource lifecycle

**Files:**
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/app.js`
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/styles.css`
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/test_prototype.js`

**Interfaces:**
- Produces: `renderImportSheet()`, `renderResourceGroup(group)`, `renderChildResource(group, child)`, `state.pending`, and mock removal actions.
- Consumes: shared sheet engine from Task 4.

- [ ] **Step 1: Add failing Import Info assertions**

Verify flags, one Mark-all action, grouped primary/derived resources, image thumbnails, conditional Ignored resources, and Debug-only information. Assert absence of `Extracted result`, `Provenance`, `Original source`, Restore, and field-level choice actions.

- [ ] **Step 2: Add failing deletion assertions**

Click a derived trash button and assert its row becomes an inline confirmation containing:

```text
Remove this resource?
This resource cannot be restored.
Your saved recipe will not change.
Cancel
Remove resource
```

Click a primary trash button and assert the group confirmation reports counts/types and explicitly retains the current cover.

- [ ] **Step 3: Run and verify failure**

Expected: FAIL because Import Info is not implemented.

- [ ] **Step 4: Implement review messages and Mark all reviewed**

Set `state.pending = { type: 'flags' }` before confirmation. Confirming adds the scenario key to `state.reviewed`, clears the Default View status, keeps recipe/resources unchanged, and announces `All import messages marked as reviewed.`

- [ ] **Step 5: Implement grouped resources and ignored section**

Render each primary as a group boundary with derived rows below it. Image rows include local thumbnails. `Ignored resources` appears only when at least one ignored derived resource remains.

- [ ] **Step 6: Implement inline child and primary confirmations**

Only the affected row or group changes to confirmation state. Confirm moves removed items into a compact type summary; no Restore action exists. Cancel and Escape restore the trash entry point and focus.

- [ ] **Step 7: Verify close behavior and cover exception**

Closing Import Info cancels `state.pending`. Removing a primary deletes its non-cover children while the current-cover child remains visible and marked `Kept as cover`.

- [ ] **Step 8: Run Import Info assertions for User and Debug roles**

Expected: all review/removal behavior passes; underlying scroll remains unchanged; no raw resource IDs appear for User.

- [ ] **Step 9: Commit Import Info**

```text
feat(ui-ux): add mobile import review sheet
```

---

### Task 6: Overflow, recipe deletion, and failure destination

**Files:**
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/app.js`
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/styles.css`
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/test_prototype.js`

**Interfaces:**
- Produces: `renderOverflow()`, `renderDeleteRecipeSheet()`, and `confirmRecipeDeletion()`.

- [ ] **Step 1: Add failing overflow and deletion assertions**

Assert `Delete recipe…` is the final separated overflow item in View and Focus, does not appear inside Media/Import Info, and opens a blocking named confirmation.

- [ ] **Step 2: Add failing dismissal and result assertions**

Verify cross/Cancel/Escape close deletion; a 140 px downward handle gesture does not close it; success shows Recipes list plus `Recipe deleted`; failure keeps the sheet open with `Recipe couldn’t be deleted. Try again.`

- [ ] **Step 3: Run and verify failure**

Expected: FAIL because overflow/deletion are absent.

- [ ] **Step 4: Implement compact overflow menu**

Use `role="menu"`, return focus to overflow on close, and render a separator before the final destructive item.

- [ ] **Step 5: Implement blocking deletion sheet**

Set the product root inert while open. Trap Tab/Shift+Tab inside the sheet. Do not attach swipe handlers. Copy names the recipe and the associated imported assets.

- [ ] **Step 6: Implement mock success and failure**

Success clears the layer and renders a mock Recipes destination. Failure keeps the layer, sets `state.deleteError = true`, and focuses the retryable destructive button.

- [ ] **Step 7: Run deletion assertions**

Expected: all modal, focus, swipe-resistance, success, and failure assertions pass.

- [ ] **Step 8: Commit destructive flows**

```text
feat(ui-ux): add mobile recipe deletion flow
```

---

### Task 7: Full responsive, accessibility, and long-content verification

**Files:**
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/test_prototype.js`
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/styles.css`
- Create: `design/recipe-detail/reviews/06-mobile-recipe-detail/ux-review.md`
- Create: `design/recipe-detail/reviews/06-mobile-recipe-detail/visual-review.md`
- Create: `design/recipe-detail/reviews/06-mobile-recipe-detail/product-fit-review.md`
- Create: `design/recipe-detail/reviews/06-mobile-recipe-detail/accessibility-review.md`
- Create: `design/recipe-detail/reviews/06-mobile-recipe-detail/responsive-long-content-review.md`
- Modify: `design/recipe-detail/prototypes/06-mobile-recipe-detail/README.md`

**Interfaces:**
- Produces the stable success marker `MOBILE_RECIPE_DETAIL_CHECKS_PASS`.

- [ ] **Step 1: Extend the browser matrix**

Run every ready/error scenario at widths 360, 390, and 430. For each, assert:

```js
assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false);
assert.deepEqual(await page.evaluate(() => [...document.images].filter(img => !img.complete || !img.naturalWidth).map(img => img.src)), []);
```

Collect console errors and page errors; fail if either list is non-empty.

- [ ] **Step 2: Add keyboard and touch-target checks**

Assert logical tab order, focus return, Escape priority, modal focus trap, and bounding boxes of primary mobile controls at least 44 px high.

- [ ] **Step 3: Add long-content preservation checks**

Expand Ingredients, scroll into later items, open/close Media, and assert the same item remains near the same viewport offset. Repeat for Focus Instructions and Import Info.

- [ ] **Step 4: Run the full test suite**

Expected final stdout:

```text
MOBILE_RECIPE_DETAIL_CHECKS_PASS
```

- [ ] **Step 5: Record five separate critiques**

Each review names the tested states, concrete findings, remaining risks, and approval status. Do not use a shared generic conclusion.

- [ ] **Step 6: Update README**

Document scope, controls, exact run command, screenshots, reviews, and the explicit Edit Mode boundary.

- [ ] **Step 7: Commit verification and reviews**

```text
test(ui-ux): verify mobile recipe detail prototype
```

---

### Task 8: Screenshot evidence and review handoff

**Files:**
- Create: `design/recipe-detail/screenshots/06-mobile-recipe-detail/mobile-normal-390x844.png`
- Create: `design/recipe-detail/screenshots/06-mobile-recipe-detail/mobile-flagged-390x844.png`
- Create: `design/recipe-detail/screenshots/06-mobile-recipe-detail/mobile-focus-ingredients-390x844.png`
- Create: `design/recipe-detail/screenshots/06-mobile-recipe-detail/mobile-focus-instructions-390x844.png`
- Create: `design/recipe-detail/screenshots/06-mobile-recipe-detail/mobile-media-sheet-390x844.png`
- Create: `design/recipe-detail/screenshots/06-mobile-recipe-detail/mobile-import-info-sheet-390x844.png`
- Create: `design/recipe-detail/screenshots/06-mobile-recipe-detail/mobile-resource-confirmation-390x844.png`
- Create: `design/recipe-detail/screenshots/06-mobile-recipe-detail/mobile-delete-recipe-390x844.png`
- Create: `design/recipe-detail/screenshots/06-mobile-recipe-detail/mobile-long-title-360x800.png`

**Interfaces:**
- Produces stable approval evidence; does not alter approved gallery entries before user approval.

- [ ] **Step 1: Capture deterministic screenshots**

Use Playwright after `networkidle`; set scenario/context through the evaluation controls and use role/name locators for interactions. Keep toolbar outside the screenshot clip so images show only the product surface.

- [ ] **Step 2: Inspect every screenshot visually**

Check text clipping, button wrapping, sheet height, focus/selection visibility, destructive copy proximity, thumbnail recognition, and long-title action reachability.

- [ ] **Step 3: Correct only demonstrated defects**

For each correction, add a regression assertion before changing CSS or behavior. Re-run the full suite after the fix.

- [ ] **Step 4: Present the prototype for user review**

Provide the direct `index.html` path, screenshot set, critique summary, and explicit unresolved visual details. Do not add the prototype to the Approved Decision Gallery until the user approves it.

- [ ] **Step 5: Commit screenshot evidence**

```text
docs(ui-ux): capture mobile recipe detail evidence
```

---

## Plan self-review

- Spec coverage: Default View, Focus, metadata disclosure, Media, Import Info, resource removal, recipe deletion, state preservation, scenarios, accessibility, and review evidence each map to an explicit task.
- Isolation: all created or modified files stay under `design/recipe-detail/`; production paths are absent.
- Scope: Edit remains a non-functional announcement; Organize Recipe, Cover Picker, checkboxes, scaling, and persistent cooking sessions remain excluded.
- Naming consistency: `state.context`, `state.focusTab`, `state.layer`, `state.pending`, `openLayer()`, `closeLayer()`, and `renderLayer()` are used consistently across tasks.
- Placeholder scan: no TBD, TODO, “similar to”, or unspecified error-handling steps remain.
