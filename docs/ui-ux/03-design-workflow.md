# UI/UX Design Workflow

## Phase 1 — Establish scope

Read the working agreement, product scope, decisions, scenarios, and decision log.

Inspect product code only when necessary to answer a functional question.

Create:

```text
design/recipe-detail/decisions/current-scope.md
```

Record:

- task being designed;
- approved constraints;
- unresolved decisions;
- states required;
- what is explicitly out of scope.

## Phase 2 — Research current patterns

Research current product interfaces and pattern libraries.

Study patterns separately:

- object/detail reading pages;
- compact metadata headers;
- two-column long-form content;
- provenance and import review workspaces;
- content editing versus organization;
- large tag and collection sets;
- focused reading or task modes;
- desktop drawers;
- mobile bottom sheets;
- warning and review states.

Save:

```text
design/recipe-detail/research/pattern-research.md
```

For every reference, record:

- product and screen;
- current source;
- exact pattern being studied;
- why it may fit;
- why it may not fit;
- what must not be copied.

References support reasoning; they are not templates to clone.

## Phase 3 — UX structure

Before styling, define:

- task;
- entry and exit points;
- primary and secondary actions;
- information hierarchy;
- progressive disclosure;
- sparse and dense states;
- desktop behavior;
- mobile behavior;
- keyboard and accessibility implications.

For unresolved decisions, produce 2–3 deliberate alternatives.

Keep approved decisions fixed.

## Phase 4 — Low-fidelity wireframes

Create low-fidelity artifacts under:

```text
design/recipe-detail/wireframes/
```

Wireframes may be:

- SVG;
- structured HTML/CSS;
- another browser-renderable format.

Use realistic labels and data.

Do not use image-generation models for the interface.

## Phase 5 — Isolated prototypes

For serious evaluation, create isolated prototypes under:

```text
design/recipe-detail/prototypes/
```

Rules:

- no production components;
- no application APIs;
- no edits to `frontend/src`;
- mock data only;
- prototype-specific CSS;
- routes or controls for required states;
- reproducible startup instructions.

A prototype should make it possible to compare variants without regenerating unrelated areas.

## Phase 6 — Browser evaluation

Capture at minimum:

- desktop normal state;
- desktop dense state;
- desktop flagged state;
- mobile normal state;
- mobile dense state;
- mobile media or overlay state where relevant.

Recommended viewports:

```text
1440 × 900
1024 × 768
390 × 844
```

## Phase 7 — Separate critiques

Create separate review files:

```text
design/recipe-detail/reviews/
├── ux-review.md
├── visual-review.md
├── product-fit-review.md
├── accessibility-review.md
└── responsive-long-content-review.md
```

Do not combine all criticism into a vague “looks good” review.

## Phase 8 — Approval gate

Before high fidelity, summarize:

- approved structure;
- rejected alternatives;
- unresolved details;
- state coverage;
- mobile implications.

Ask for user approval.

Do not move to production implementation until the user explicitly starts an implementation phase.
