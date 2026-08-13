# Recipe Detail UI/UX Design

## Scope

This directory is the isolated workspace for Recipe Detail UI/UX design. It does not authorize production implementation.

The goal is to produce:

- product-reference research;
- information architecture;
- user flows;
- low-fidelity wireframes;
- mockups;
- isolated HTML/CSS/JavaScript prototypes;
- structured UX and visual critiques;
- durable design-to-implementation handoff context.

## Hard production-code boundary

For a Recipe Detail design task, do not modify:

- `frontend/src`;
- production frontend styles;
- backend code;
- API clients or schemas;
- database models or migrations;
- application routing;
- production tests;
- deployment configuration.

Prototype code is allowed only under `design/recipe-detail/prototypes/`. It must use mock data and have no dependency on production components or APIs.

## Existing UI is not a design reference

Do not copy, preserve, restyle, incrementally improve, or infer visual decisions from current production pages or CSS.

Production code may be inspected only to determine:

- available data;
- supported actions;
- business states;
- permissions;
- constraints;
- error cases.

Never justify a design decision with “this matches the current page.”

## Source-of-truth order

Read these files before Recipe Detail design work:

1. `docs/ui-ux/00-working-agreement.md`
2. `docs/ui-ux/01-product-scope.md`
3. `docs/ui-ux/02-recipe-detail-decisions.md`
4. `docs/ui-ux/03-design-workflow.md`
5. `docs/ui-ux/04-realistic-data-scenarios.md`
6. `docs/ui-ux/05-review-checklist.md`
7. `docs/ui-ux/07-decisions-log.md`

When they conflict, the later explicit decision in `07-decisions-log.md` wins.

## Required working method

- Use current, relevant product references before proposing visual solutions.
- Analyze UX structure before visual styling.
- Present 2–3 deliberate alternatives when a decision is genuinely unresolved.
- Explain trade-offs and recommend one alternative.
- Preserve approved decisions instead of regenerating the whole design.
- Test sparse, normal, dense, error, review, and responsive states.
- Use realistic content, not lorem ipsum or meaningless placeholder layouts.
- Use isolated browser prototypes for serious evaluation.
- Capture screenshots at agreed desktop and mobile sizes.
- Run separate UX, visual, product-fit, accessibility, responsive, and long-content reviews.
- Ask for approval before moving from low fidelity to high fidelity.

## Image-generation rule

Do not use image generation as the primary UI design method. Do not generate UI screenshots with an image model unless the user explicitly requests it.

## Artifact locations

```text
design/recipe-detail/
├── research/
├── wireframes/
├── prototypes/
├── screenshots/
├── reviews/
└── decisions/
```

Keep each approved iteration. Do not silently overwrite approved design evidence.

## Completion rule

A design iteration is complete only when it includes:

- the task and state being designed;
- references or patterns considered;
- the proposed structure;
- unresolved questions;
- realistic dense-data coverage;
- desktop and mobile implications;
- an explicit critique;
- verification evidence;
- a user approval status.
