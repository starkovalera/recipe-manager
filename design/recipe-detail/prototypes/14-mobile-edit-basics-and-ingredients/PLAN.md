# Mobile Edit Basics and Ingredients Refinement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a preserved Prototype 14 that refines the approved mobile Recipe Edit baseline by regularizing Basics controls and removing mobile ingredient reordering.

**Architecture:** Copy Prototype 13 into a new isolated static prototype, then change only the Basics form, the mobile Ingredients list, their assertions, and their captured evidence. Keep the compact edit header, single-open accordion, ingredient editor sheet, Overflow behavior, dirty draft behavior, and global navigation unchanged.

**Tech Stack:** Semantic HTML, isolated CSS, vanilla JavaScript, Node Playwright assertions with local Microsoft Edge.

## Global Constraints

- Work only under `design/recipe-detail/`; do not modify production code.
- Keep Prototype 13 and all earlier prototypes unchanged.
- Primary viewport is `390 × 844`; also verify 360 and 430 CSS-pixel widths.
- Source is a fixed select with exactly `Manual`, `Instagram`, `Threads`, `TikTok`, and `Other`.
- Difficulty is a fixed select with `Not set`, `Easy`, `Moderate`, and `Hard`.
- Personal rating is a fixed select with `Not rated`, `1 out of 5`, `2 out of 5`, `3 out of 5`, `4 out of 5`, and `5 out of 5`.
- Mobile Ingredients has no drag-and-drop, reorder handle, reorder instruction, or accessible move commands. Ingredient editing through the summary button and deletion through the trash action remain.
- Do not modify Git refs or create a commit for this iteration.

---

### Task 1: Prototype 14 field and list refinement

**Files:**
- Create: `design/recipe-detail/prototypes/14-mobile-edit-basics-and-ingredients/index.html`
- Create: `design/recipe-detail/prototypes/14-mobile-edit-basics-and-ingredients/styles.css`
- Create: `design/recipe-detail/prototypes/14-mobile-edit-basics-and-ingredients/app.js`
- Create: `design/recipe-detail/prototypes/14-mobile-edit-basics-and-ingredients/README.md`

**Interfaces:**
- Consumes the shell and interaction model from Prototype 13.
- Preserves `window.mobileEditPrototype.getState()` for browser assertions.
- Produces a `.basics-grid` with one full-width title row and three equal two-column rows.
- Produces ingredient rows containing only `.row-summary` and `.trash` actions.

- [ ] **Step 1: Copy the Prototype 13 product files into the new version**

Copy `index.html`, `styles.css`, and `app.js` as the starting baseline. Do not change Prototype 13.

- [ ] **Step 2: Replace the Basics markup**

Render this order and grouping:

```text
Recipe title                     [full width]
Source              | Author     [equal columns]
Cooking time        | Servings   [equal columns]
Difficulty          | Rating     [equal columns]
```

Use semantic `select` controls for Source, Difficulty, and Rating with the exact values from Global Constraints. Use `Instagram`, `Moderate`, and `4 out of 5` as realistic selected mock values. Update the Basics section count from `5 fields` to `7 fields`.

- [ ] **Step 3: Normalize the Basics grid**

Use one equal `1fr 1fr` column definition for all paired rows. Remove the unequal `.two-up.facts` override. Keep the title full-width and keep all input/select controls the same height.

- [ ] **Step 4: Remove mobile ingredient reordering**

Remove `Drag to reorder`, every ingredient `.handle`, and all ingredient reorder labels or commands. Change ingredient rows to `minmax(0, 1fr) 44px`; retain the full summary button with chevron and the standard trash action.

- [ ] **Step 5: Document the refinement**

State that this version supersedes mobile ingredient reordering only; desktop ingredient reordering and instruction reordering are unchanged and remain outside this iteration.

### Task 2: Verification and preserved evidence

**Files:**
- Create: `design/recipe-detail/prototypes/14-mobile-edit-basics-and-ingredients/test_prototype.js`
- Create: `design/recipe-detail/prototypes/14-mobile-edit-basics-and-ingredients/capture_screenshots.js`
- Create: `design/recipe-detail/screenshots/edit-mode/14a-mobile-edit-basics-v1.png`
- Create: `design/recipe-detail/screenshots/edit-mode/14b-mobile-edit-ingredients-v1.png`
- Modify: `design/recipe-detail/decisions/07-edit-mode-current-decisions.md`
- Modify: `design/recipe-detail/decisions/decision-log.md`

**Interfaces:**
- Consumes the Prototype 14 DOM and `window.mobileEditPrototype.getState()`.
- Produces deterministic pass marker `MOBILE_EDIT_REFINEMENT_CHECKS_PASS`.

- [ ] **Step 1: Update assertions for Basics**

At 360, 390, and 430 px, verify no horizontal overflow, `Basics 7 fields`, the exact Source/Difficulty/Rating option lists, equal paired-control widths, and equal control heights.

- [ ] **Step 2: Update assertions for Ingredients**

Verify ingredient rows have no `.handle`, no reorder copy, and still expose the summary editor and trash action. Preserve existing assertions for the ingredient sheet, single-open accordion, compact header, Overflow, auxiliary contexts, global navigation, dirty guard, and Save.

- [ ] **Step 3: Capture focused evidence**

Capture one 390 × 844 screenshot with Basics expanded and one with Ingredients expanded. Keep Prototype 13 screenshots unchanged.

- [ ] **Step 4: Record the approved decisions**

Record Source as the five-value fixed set, the equal Basics grid, the added Difficulty/Rating fields and their prototype scales, and the removal of mobile ingredient reordering. Explicitly note that backend persistence for Difficulty and Personal rating remains future work.

- [ ] **Step 5: Run verification**

Run the prototype Playwright test, screenshot capture, a mojibake scan over the new text files, link/path checks relevant to the new prototype, and `git diff --check`.
