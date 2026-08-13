# Design Artifact Instructions

## Scope

This directory contains non-production product-design artifacts.

Allowed content includes:

- product-reference research;
- information architecture and user flows;
- wireframes and mockups;
- isolated HTML/CSS/JavaScript prototypes with mock data;
- screenshots, critiques, reviews, and decision records;
- design-to-implementation handoff material.

## Boundary with the application

- Files under `design/` are evidence and specifications, not production application code.
- Do not depend on production components, application APIs, runtime configuration, or production styles from a prototype.
- Do not modify `frontend/`, `backend/`, schemas, migrations, production tests, routing, or deployment as part of a design-only task.
- If the user requests implementation, leave the design artifact intact and implement separately in the appropriate production subtree under its applicable instructions.
- Existing production UI may be inspected for functional scope, supported actions, roles, permissions, constraints, business states, and edge cases. Do not use it as the visual baseline for an active redesign.

## Artifact discipline

- Preserve approved iterations; create a new numbered iteration for material alternatives.
- Use realistic content and include sparse, normal, dense, error, and responsive states where relevant.
- Store durable decisions, prototypes, screenshots, and reviews inside the tracked `design/` hierarchy.
- Temporary brainstorming output is not an implementation source until promoted into permanent tracked artifacts.
- Do not use image generation for UI screenshots unless the user explicitly requests it.

## Completion

A serious design iteration should identify its task, approved inputs, unresolved questions, desktop/mobile implications, critique, verification, and approval status.

More specific instructions in descendant `AGENTS.md` files take precedence for their subtree.
