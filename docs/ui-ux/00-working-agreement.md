# Recipe Manager UI/UX Working Agreement

## Core problem

The problem is the quality of design ideas, not the absence of a design tool.

The user is not expected to express preferences in professional design terminology. Functional requirements, ordinary-language feedback, comparisons, and negative reactions are sufficient input. The design agent must translate them into professional UX and UI decisions.

## Design phase boundary

Current production pages and styles are not a design baseline.

The repository may be inspected only to understand:

- functional scope;
- domain data;
- supported user actions;
- business invariants;
- permissions and roles;
- realistic states and constraints.

Do not use the current page composition, component structure, CSS, spacing, typography, colors, or navigation as a reference.

Do not modify production code during this phase.

Isolated prototype code under `design/recipe-detail/prototypes/` is allowed because serious evaluation requires real layout behavior, realistic content, responsive states, and browser screenshots.

## Required design process

1. Start from current, relevant product references rather than inventing the interface from scratch.
2. Analyze concrete patterns separately:
   - navigation;
   - object/detail pages;
   - inline editing;
   - structured forms;
   - long lists;
   - tags and collections;
   - import and provenance flows;
   - empty, loading, error, sparse, dense, and flagged states;
   - desktop and mobile behavior.
3. Separate UX structure from visual styling:
   - first define tasks, hierarchy, states, actions, and responsive behavior;
   - then choose typography, color, spacing, surfaces, and visual character.
4. Present 2–3 deliberate directions for unresolved decisions, with trade-offs and a recommendation.
5. Explain which references and product patterns support each direction.
6. Preserve approved decisions. Do not regenerate the entire design when only one detail changes.
7. Test designs with realistic and difficult data.
8. Run separate review passes:
   - UX critique;
   - visual critique;
   - product-fit critique;
   - accessibility review;
   - responsive and long-content review.
9. Use real HTML/CSS prototypes for serious evaluation.
10. Do not use image generation as the primary UI design method.
11. Do not generate images unless the user explicitly asks.

## Visual anti-patterns

Avoid:

- generic beige culinary-blog styling;
- decorative serif typography as the main interface font;
- a card around every block;
- excessive shadows and large rounded corners;
- pills used for nearly every control;
- oversized hero sections that displace useful information;
- generic sidebars with decorative marketing copy;
- excessive whitespace and artificially low information density;
- mobile layouts produced by shrinking desktop layouts;
- cheap Wix, Webflow, or template-builder aesthetics;
- decorative effects that do not improve task completion;
- interfaces that look like lifestyle sites rather than productivity tools.

## Feedback interpretation

The user may say:

- old-fashioned;
- cheap;
- template-like;
- overloaded;
- too empty;
- inconvenient;
- closer to or farther from the desired result.

Translate this feedback into concrete hypotheses about hierarchy, density, structure, typography, spacing, component treatment, visual noise, interaction cost, and product fit.

## Standing rule

Prioritize a modern, practical, product-oriented interface over decorative recipe-app aesthetics.
