# Recipe Detail — Current Design Scope

Status: Approved; U1 and U2 resolved  
Updated: 2026-07-22

## Purpose of this iteration

Preserve the fixed Recipe Detail UX scope, its completed research, and the approved resolutions of U1 and U2. This document remains the current boundary for the next explicitly approved design phase.

This is a design-only phase. It does not authorize production implementation.

## Hard boundary

- Do not modify production frontend or backend code, APIs, schemas, production styles, application routes, tests, or deployment configuration.
- Do not use the existing production frontend as a visual reference.
- Existing code may be inspected only for functional scope: data, actions, roles, permissions, constraints, business states, and edge cases.
- Do not preserve, restyle, or incrementally improve the current Recipe Detail page.
- Do not use image generation.
- Do not create a polished final UI before low-fidelity structure and user approval.
- Keep every design artifact under `design/recipe-detail/`.

## Approved Recipe Detail decisions

### 1. Information architecture

Recipe Detail is not one permanent long page, form, or dashboard. It is divided into distinct task contexts:

```text
Recipe
├── Default Recipe View
├── Cooking Focus
│   └── Optional Media
├── Import Info
├── Edit Recipe Content
├── Organize Recipe
└── Cover Picker
```

Global application navigation may appear only as a neutral shell in this iteration; redesigning it is out of scope.

### 2. Default Recipe View

The Default Recipe View is primarily for reading and using a saved recipe.

Its approved desktop foundation is:

- a compact header;
- a fixed-width Ingredients column on the left;
- a wider Instructions column on the right;
- Estimated Nutrition below Ingredients;
- Cooking Notes below Instructions.

Ingredients and Instructions are dominant. Sections must not each be wrapped in a large card.

The compact header must:

- use a moderately sized, recognizable cover rather than a hero image;
- make the recipe title the strongest element;
- keep primary metadata and page actions compact;
- keep secondary organization metadata from competing with the title and actions.

Source and author remain distinguishable but have no visible `Source` or `Author` field labels in Default View. They belong in a compact inline row with time and servings, using separators, typography, icons, or spacing to preserve meaning.

For imported recipes, the main actions are:

```text
Cook / Focus · Edit · Import info · Overflow
```

- `Cook / Focus` is primary.
- `Edit` is secondary.
- `Import info` is a neutral secondary action.
- Rare and destructive recipe actions belong in overflow.

For every imported recipe:

- `Import info` is available whether or not review flags exist;
- the neutral `Import info` action has no warning icon;
- when no unresolved review flags exist, the ordinary Default Recipe View opens normally and no warning banner is shown.

When unresolved review flags exist, the approved entry behavior is:

- open the ordinary Default Recipe View rather than redirecting to Import Info;
- show a concise status before recipe content with a clear link to Import Info;
- keep detailed flags, evidence, and provenance inside Import Info;
- keep the persistent `Import info` action neutral and free of warning icons;
- restore the same Default View position when returning from Import Info.

Manual recipes do not show an Import Info entry point.

Tags and Collections belong in a compact upper-right metadata area, separate from the cover and primary metadata. Both use a stable fixed visible length and `+N` (or equivalent progressive disclosure) for overflow. Large sets must not create a tag cloud, grow the header unpredictably, or displace the title or actions.

Difficulty and Personal rating occupy one compact leading row in the upper-right secondary metadata area, followed by Collections and then Tags. The approved order is:

```text
Difficulty · Personal rating
Collections
Tags
```

This group must remain secondary to the title, inline source/author/time/servings context, primary actions, and any approved import-review status. Cuisine, meal type, dietary attributes, and other management metadata may be available compactly elsewhere in the organization context, but they must not compete with recipe content.

The Default Recipe View must not permanently expose:

- source lifecycle controls;
- detailed review flags;
- provenance or extraction details;
- imported-resource statuses or resource IDs;
- eligible debug information;
- source deletion or restoration controls;
- full edit forms.

### 3. Import Info

Import Info is a separate working context available from the neutral `Import info` action for every imported recipe. It is useful even when no review flags exist; it is not merely an error-resolution screen.

It may contain:

- the imported recipe result;
- source URLs, imported text, and imported images;
- used, ignored, deleted, and restorable sources;
- review flags when present;
- provenance and extraction information;
- source and author corrections;
- eligible debug information;
- information about which materials were used or ignored.

The preferred desktop structure is a split view: extracted recipe result on one side and sources, flags, provenance, and eligible debug information on the other. Mobile must use a purpose-built sequential, tabbed, or comparable structure rather than compressed desktop columns.

Cover selection, recipe organization, and cooking-focused presentation are not primary Import Info tasks.

### 4. Edit Recipe Content

Content editing is separate from organization metadata. It covers title, source and author, the cover entry point, servings, cooking time, ingredients, instructions, notes, and estimated nutrition.

It must not be one uninterrupted long form. Ingredients and instructions must support adding, editing, deleting, and reordering. Source lifecycle management, flags, provenance, and debug information do not appear here.

### 5. Organize Recipe

Organization is a separate context for Tags, Collections, personal rating, difficulty, cuisine, meal type, dietary attributes, and other search or management properties. It must not become a continuation of the recipe-content form.

### 6. Cover Picker

Cover selection is separate from source review. It shows the current cover, available images, selected image, `Use as cover`, custom upload, and future crop or positioning controls when needed.

It does not show debug information, resource IDs, lifecycle statuses, or source deletion and restoration controls.

### 7. Cooking Focus

Cooking Focus is a simplified recipe view, not a persistent cooking-session system.

It shows:

- compact recipe title;
- servings and portion scaling;
- ingredients;
- instructions;
- cooking notes;
- an exit action.

Estimated nutrition may remain compactly available but is not central.

It hides the large cover, source and author, Tags and Collections, rating and classifications, flags, provenance, debug information, administration, and source management.

It supports temporary ingredient checks, temporary completed-step states, easy Ingredients/Instructions switching on mobile, keep-screen-awake when technically possible, and return to the full recipe without losing reading position. Temporary cooking state does not need to persist after leaving the mode in the first version.

### 8. Optional media in Cooking Focus

Show `Media · N` only when media exists. Media is closed by default.

On desktop, media opens in a right-side drawer while Ingredients and Instructions remain visible. On mobile, it opens in a bottom sheet that may expand upward. Opening and closing media must preserve ingredient checks, completed steps, and recipe scroll position.

Media may show thumbnails, enlarged preview, understandable external-link actions, image origin or short caption, source platform, author or source label, and a current-cover marker when useful.

It does not show resource IDs, technical statuses, extraction flags, debug data, or source deletion and restoration. Embedded video and automatic step-level media association are not required for the first version.

### 9. Required state coverage

Later low-fidelity artifacts and prototypes must cover realistic content rather than placeholders. Required coverage includes:

- normal imported recipe with no flags;
- imported recipe with unresolved flags;
- manual recipe;
- long title with no cover;
- 50 Tags and 20 Collections;
- 45–50 ingredients;
- 35–40 long instruction steps;
- long cooking notes;
- complete, partial, missing, and clearly estimated nutrition;
- multiple used, ignored, deleted, and restorable sources;
- eligible debug role;
- mobile cooking and media behavior;
- loading, missing, failed-load, failed-save, failed-resource-action, empty, and unavailable-media states.

Desktop, tablet, and mobile implications must be designed intentionally; mobile is not a shrunken desktop layout.

## Genuinely unresolved UX decisions

No Recipe Detail structural UX decisions from this scope remain unresolved.

U2 is approved as **B2**: Difficulty and Personal rating lead the upper-right secondary metadata group, followed by Collections and Tags. The comparison and refinement are recorded in:

- `design/recipe-detail/wireframes/02-difficulty-rating-placement-comparison.md`;
- `design/recipe-detail/wireframes/03-secondary-metadata-order-comparison.md`;
- `design/recipe-detail/decisions/02-u2-difficulty-rating-placement.md`.

## Explicitly out of scope

- production implementation;
- global navigation redesign;
- a final design system or polished final UI;
- nutrition based on actual products or weights used while cooking;
- cooking batches or persistent cooking sessions;
- cooked dish weight, actual-portion nutrition, or consumption tracking;
- automatic step-level media mapping;
- embedded video in the first Cooking Focus version.

## Focused reference-research plan

### Research-method alternatives

1. **Recommended — pattern-led comparison matrix.** Compare the same Recipe Detail question across several current products and pattern systems. This keeps the work focused, exposes trade-offs, and reduces the risk of cloning one product.
2. **Product-led teardown.** Study one product end to end. This preserves interaction coherence but risks importing assumptions and visual conventions that do not fit Recipe Manager.
3. **Design-system-only review.** Use component guidance for drawers, sheets, warnings, and disclosure. This is strong for behavior and accessibility but too abstract to validate real dense-data workflows by itself.

Proceed with the pattern-led matrix, using product interfaces for workflow evidence and design systems only to check overlay and accessibility behavior.

### Current reference set and questions

| Reference | Exact pattern to study | Recipe Manager question | Important non-fit risk |
| --- | --- | --- | --- |
| [Linear issue editing and properties](https://linear.app/docs/editing-issues) | Compact object detail, direct editing, property changes, and secondary activity | How can a strong title and primary content coexist with compact actionable metadata? | Issue-tracker urgency and keyboard density should not dictate recipe-reading behavior. |
| [Airtable record detail](https://support.airtable.com/docs/airtable-interface-layout-record-detail) and [record history](https://support.airtable.com/docs/record-level-revision-history-overview) | Structured record detail, related data, configurable field groups, and secondary history | How should core recipe content remain distinct from organization and provenance contexts? | Generic database field layouts can feel form-heavy and weaken reading hierarchy. |
| [Notion database properties](https://www.notion.com/help/database-properties) | Property visibility, multi-select metadata, and page-level organization | How should dense Tags, Collections, and secondary properties disclose without destabilizing the header? | Unbounded property lists and chip-heavy presentation must not be copied. |
| [GitHub pull-request review](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests) | A dedicated review context with filtering and navigation through large evidence sets | What should remain in Import Info rather than leaking into Default View, and how should unresolved work stay actionable? | Code-review terminology and tab structure are domain-specific. |
| [Apple Books reading behavior](https://support.apple.com/guide/iphone/read-books-in-the-books-app-iphc1af7c57/ios) | Focused reading, temporary controls, navigation, and return to reading location | Which controls should disappear in Cooking Focus, and how should users return without losing position? | Paginated book reading is not the same as scanning ingredients and executing ordered steps. |
| [Carbon side-panel guidance](https://carbondesignsystem.com/elements/2x-grid/usage/) | Keeping page context visible while supplementary content opens | How can desktop cooking media open without destroying recipe context or column usability? | Enterprise side panels can be too wide or interaction-heavy for passive media. |
| [Android Material 3 bottom sheets](https://developer.android.com/develop/ui/compose/components/bottom-sheets) | Expandable mobile supplementary content and explicit sheet state | How should mobile media reveal, expand, dismiss, and return to the same cooking position? | Platform component styling is not a visual direction for the web product. |

### Evidence to capture

For every reference, record the current source and date, exact screen or behavior, entry and exit model, hierarchy, progressive disclosure, dense-data behavior, mobile implications, accessibility implications, fit, non-fit, and a principle that can be tested without copying the source.

The research must answer:

- Does unresolved status justify changing the initial destination, or is a warning inside Default View more predictable?
- How do neutral information actions remain neutral while a separate context carries actionable warnings?
- How can a compact object header disclose large metadata sets without becoming a tag cloud?
- Does difficulty and rating read as primary usage metadata or secondary organization metadata?
- Which desktop drawer and mobile-sheet behaviors preserve context and temporary state?
- Which patterns help long ingredients and instructions remain scannable without card repetition?

### Research output

Create `design/recipe-detail/research/pattern-research.md` after this scope is approved. Organize it by pattern question rather than by product. End with evidence-backed recommendations for U1 and U2, plus explicit principles for the already-approved structure. Do not create visual styling or copy a source layout during research.

## First low-fidelity artifact after research

Produce a behavior-first comparison storyboard for **U1: entry behavior with unresolved review flags**.

The artifact should compare:

- control: imported recipe with no flags opens the ordinary Default Recipe View;
- Variant A: imported recipe with unresolved flags opens Import Info;
- Variant B: imported recipe with unresolved flags opens Default View with a concise status and link to Import Info.

Use the same realistic flagged recipe and keep all approved layout decisions fixed. Show entry, destination, route back to Default View, and mobile implications. Do not introduce visual styling beyond what is needed to understand hierarchy and flow.

This artifact comes first because U1 changes the user's initial context and recovery path. A separate, second paired header artifact should compare U2 without changing any other variable.

U1 is now approved as **Variant B: Default Recipe View with a concise status linking to Import Info**. The comparison artifact and decision rationale are recorded in `design/recipe-detail/wireframes/01-flagged-entry-behavior-comparison.md`.

Proposed future path (not created in this step):

```text
design/recipe-detail/wireframes/01-flagged-entry-behavior-comparison.*
```

## Scope critique

- The reference set intentionally favors productivity and structured-data products over recipe apps, which protects the product-oriented direction but requires a separate check that reading and cooking remain calm and legible.
- U1 and U2 were isolated during comparison so research and refinement did not silently reopen approved structure.
- Both low-fidelity decisions are now resolved; their comparison artifacts remain as the decision trail.
- Dense and mobile states are requirements, not optional polish.

## Current approval state

- Current scope: approved.
- Reference research: approved.
- U1 flagged-entry behavior: approved as Variant B.
- U2 difficulty and personal-rating placement: approved as B2.
- Low-fidelity structure and interaction behavior: approved through Prototype 05.
- Consolidated foundation: `design/recipe-detail/decisions/06-approved-ux-foundation.md`.
- Reusable cross-page patterns: `design/recipe-detail/reusable-product-patterns.md`.
- Visual-direction exploration is the next design stage; no high-fidelity or production implementation has been produced yet.
