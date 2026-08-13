# Recipe Detail — Current Design Scope

Status: structural UX approved; Recipe Edit core partially complete; visual execution not started
Updated: 2026-08-13

## Purpose

This file is the current boundary for Recipe Detail design work. It replaces the earlier U1/U2 comparison-stage snapshot. Historical wireframes and prototypes remain decision evidence, but later entries in `docs/ui-ux/07-decisions-log.md` and the numbered decision files supersede them.

This remains a design-only phase. It does not authorize production implementation.

## Hard boundary

- Do not modify production frontend or backend code, APIs, schemas, routes, tests, production styles, or deployment configuration.
- Do not use the current production frontend as a visual reference.
- Keep isolated prototype code and mock data under `design/recipe-detail/`.
- Preserve approved behavior while exploring unfinished sections or visual directions.
- Do not convert low-fidelity prototypes directly into production components.

## Approved context model

```text
Recipe Detail
├── Default View
├── Cooking Focus
├── Edit Recipe
├── Organize Recipe
├── Manage Media / Cover selection
└── One auxiliary slot
    ├── Media
    └── Import Info
```

These contexts have separate task and draft boundaries. Import resource actions take effect independently from the Recipe Edit draft; Manage Media owns its own draft.

## Approved Recipe Detail foundation

- Default View uses a compact header, corrected-B action band, fixed Ingredients column, wider Instructions column, bounded long content, and stable upper-right metadata.
- Source identity and cooking facts are separate compact rows without visible `Source` or `Author` labels.
- Difficulty and Personal rating appear above Collections and Tags. Collections and Tags use fixed disclosure with `+N`.
- Desktop Import Info is reached through Overflow. On first entry into a flagged imported recipe, it auto-opens once per recipe visit.
- Media and Import Info share one auxiliary slot but retain separate entry points and content.
- Imported resources are grouped by primary/derived hierarchy; ignored resources are conditional; image resources use thumbnails.
- Primary and secondary resource removal use local irreversible confirmation and state explicitly that the saved recipe content does not change.
- Cooking Focus is a simplified reading/execution mode. Ingredient checkboxes and portion scaling are deferred.
- Recipe deletion is an Overflow-only irreversible action with blocking desktop and mobile confirmation.
- The product-wide mobile shell is `Recipes / Collections / Add / Notifications / Profile` with hierarchy-aware top bars and one modal sheet layer.

The consolidated contract is `06-approved-ux-foundation.md`; reusable cross-page lessons are in `../reusable-product-patterns.md`.

## Approved Recipe Edit foundation

### Shared model

- One Recipe Edit page owns one recipe-level draft and one global Save outcome.
- Media and Import Info remain auxiliary and preserve the Edit draft, active section, and scroll position.
- Manage Media is a separate workspace and therefore invokes the dirty-draft guard when entered from a dirty Edit draft.
- Ingredient notes are not shown or edited.

### Desktop

- Continuous page, sticky section rail, ordinary scrolling, and scrollspy.
- Two-zone Basics without card containers.
- Compact Ingredients rows with reorder, optional Quantity, fixed Unit, required name, and trash action.
- Hybrid validation, linked failed-Save summary, rail error counts, and centered unsaved-changes guard.

### Mobile

- Always-compact `Back / recipe title / Save / Overflow` toolbar.
- Unchanged global navigation and one-open accordion for Basics, Ingredients, Instructions, Cooking notes, and Estimated nutrition.
- Compact ingredient summary rows, no mobile reorder, and a single-item editing sheet.
- Hybrid Basics controls: Source selection sheet, direct Difficulty segments, centered five-star whole-value rating.
- Failed Save uses a linked summary above the accordion and text error counts on affected sections.
- The approved dirty-draft bottom sheet uses `Save changes`, destructive-only `Discard changes`, and neutral `Keep editing`. Safe dismissal retains the draft.

The detailed contract is `07-edit-mode-current-decisions.md`. Prototype 16 is the latest approved mobile behavior evidence.

## Completed artifact sequence

- Research and scope: complete.
- U1/U2 structural comparisons: complete and superseded by later decisions where noted.
- Desktop Default/Focus/Media/Import Info behavior: approved through Prototype 05.
- Mobile Recipe Detail and Cooking Focus: approved through Prototype 06.
- Global mobile shell: approved through Prototype 10.
- Mobile Recipe Edit shell and Save placement: approved through Prototypes 11–13.
- Mobile Basics and Ingredients: approved through Prototypes 14–15.
- Mobile validation and unsaved-changes guard: approved through Prototype 16.
- Desktop Recipe Edit Basics, Ingredients, validation, and guard: approved low-fidelity direction.

## Remaining design work

### Recipe Edit completion

- Instructions editing, deletion, desktop reordering, mobile presentation, and validation.
- Cooking notes editing and validation.
- Estimated nutrition editing, incomplete/missing states, and validation.
- Save in-progress, success, server-failure, and retry presentation.
- Mobile software-keyboard behavior.
- Sparse, dense, long-label, localization, and request-failure stress tests.

### Separate contexts

- Detailed desktop and mobile Manage Media workspace, upload capacity, cover replacement, removal, validation, and its independent save/cancel draft.
- Detailed Organize Recipe behavior.
- Final decision on whether cover selection remains embedded in Manage Media or requires a narrower Cover Picker entry state.

### Visual execution

- Typography, palette, icons, cover/thumbnail treatment, density, dividers, surfaces, focus/hover/selected/error states, and restrained motion.
- Representative desktop and mobile states required by `../visual-execution-brief.md`.
- Accessibility, responsive, localization, and long-content reviews before implementation handoff.

## Still unresolved

- Exact Unit dictionary, localized aliases, and ordering.
- Exact desktop threshold where the section rail becomes compact.
- Exact maximum lengths for Title, Author, and Ingredient name.
- Detailed Instructions, Cooking notes, Nutrition, Manage Media, and Organize Recipe behavior.
- Final visual system and high-fidelity responsive execution.

## Explicitly deferred or out of scope

- Production implementation during this phase.
- Actual cooking-session nutrition, cooked weight, consumption tracking, and persistent cooking sessions.
- Portion scaling until its real-product calculation scenario is designed.
- Ingredient/step completion checkboxes in the first Cooking Focus iteration.
- Automatic step-level media mapping and embedded video.

## Next gate

Complete the remaining Recipe Edit sections, beginning with Instructions, then Cooking notes and Estimated nutrition. Preserve Prototype 16 validation and guard behavior. After the feature-level UX is complete, design the separate Manage Media workspace and proceed to the visual-direction comparison defined in `../visual-execution-brief.md`.
