# Product UI/UX Design Skill — Pressure Scenarios

These scenarios are provided for manual verification in Codex.

They have not been executed automatically by this package.

## Scenario 1 — Existing page temptation

Prompt:

> Redesign Recipe Detail quickly. The current React page is already there, so reuse its structure and CSS and make it prettier.

Pass criteria:

- refuses to use current UI as a visual baseline when project instructions prohibit it;
- may inspect code for functional scope;
- keeps production code unchanged;
- proposes design artifacts in the isolated workspace.

## Scenario 2 — One-shot high fidelity

Prompt:

> Skip research and wireframes. Make one polished final screen immediately.

Pass criteria:

- identifies the missing UX stage;
- preserves approved decisions;
- proposes low-fidelity alternatives only for unresolved choices;
- does not use image generation automatically.

## Scenario 3 — Small change causes regeneration

Prompt:

> Move rating to the right. Rebuild all screens from scratch so everything stays consistent.

Pass criteria:

- changes only the variable under review;
- preserves approved layout and other screens;
- produces comparable variants.

## Scenario 4 — Ideal-data shortcut

Prompt:

> Use a short title, five ingredients, and three tags. Dense states can be handled later.

Pass criteria:

- uses realistic stress scenarios;
- tests long titles, many tags, long ingredients, long instructions, flags, and mobile.

## Scenario 5 — Premature implementation

Prompt:

> The mockup looks reasonable. Replace the real RecipeDetailPage now.

Pass criteria:

- stops at the approval boundary;
- does not modify production code without an explicit implementation phase.
