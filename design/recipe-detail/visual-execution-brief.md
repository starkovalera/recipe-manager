# Recipe Detail Visual Execution Brief

Status: ready for visual-direction exploration; high fidelity not yet produced  
Updated: 2026-07-23

## Objective

Translate the approved UX foundation into a modern, practical product interface without changing its information architecture or interaction model.

## Fixed inputs

Read before visual work:

1. `decisions/06-approved-ux-foundation.md`;
2. `reusable-product-patterns.md`;
3. `research/pattern-research.md`;
4. `prototypes/05-main-actions-and-responsive-panels/index.html`;
5. `reviews/05-main-actions-and-responsive-panels/`.

The v5 prototype is behavioral evidence, not a visual style reference. Its fonts, colors, borders, spacing, cover placeholders, and icons are intentionally low fidelity.

## Visual character to pursue

- Product-oriented rather than editorial or lifestyle-oriented.
- Calm enough for long reading and cooking.
- Dense enough for serious recipe management.
- Precise, contemporary, and accessible.
- Structured through typography, spacing, alignment, and dividers.
- One deliberate visual signature grounded in recipe work, not generic decorative food styling.

## Avoid

- beige culinary-blog defaults;
- decorative serif as the dominant interface face;
- oversized cover hero;
- a card around every content block;
- excessive rounded pills, shadows, gradients, or whitespace;
- tag clouds that compete with the title;
- shrinking desktop UI to make mobile;
- treating warning, selection, hover, and destructive states as color-only variations;
- copying the current production frontend.

## Open visual axes

Create 2–3 deliberate visual directions that keep identical UX structure while varying:

- interface and display typography;
- neutral and semantic palette;
- density and spacing rhythm;
- divider and surface treatment;
- cover and thumbnail presentation;
- icon family and stroke weight;
- focus, hover, active, selected, warning, and destructive states;
- one restrained motion concept.

For each direction, explain product fit, risks, and what must not be copied from references. Recommend one direction for high-fidelity development.

## First visual artifact

Produce an otherwise identical Default View visual-direction comparison at 1440 px using the flagged imported recipe. Include:

- approved corrected-B action band;
- real-length title and metadata;
- compact review status;
- Ingredients and Instructions content;
- upper-right metadata;
- closed auxiliary panels.

Then validate the recommended direction with these control states before expanding scope:

1. 1280 px with Media overlay;
2. 1024 px with Import Info overlay;
3. 390 px Default View action rows;
4. 390 px Media sheet;
5. desktop Import Info with ignored resources and removal confirmation;
6. desktop and mobile recipe-deletion confirmation.

## Evaluation gates

Run separate reviews for:

- visual hierarchy and product distinctiveness;
- long-content readability;
- status and destructive-state clarity;
- accessibility and focus visibility;
- responsive behavior and localization pressure;
- consistency with transferable product patterns.

Do not proceed to production implementation until the visual direction and representative responsive states are explicitly approved.
