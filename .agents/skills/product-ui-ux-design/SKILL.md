---
name: product-ui-ux-design
description: Use when designing or redesigning multi-screen product interfaces, UX flows, wireframes, mockups, responsive states, or isolated browser prototypes before production implementation.
---

# Product UI/UX Design

## Core principle

Design a product workflow before styling a screen. Use evidence, deliberate alternatives, realistic states, browser prototypes, and separate critiques.

## Required inputs

Read the nearest `AGENTS.md` and the project UI/UX source-of-truth files before proposing a design.

If approved decisions exist, preserve them. Explore only unresolved decisions.

## Workflow

1. **Set the boundary**
   - State the task, approved decisions, unresolved decisions, states, and out-of-scope work.
   - Do not edit production code during a design-only phase.

2. **Learn functional scope**
   - Inspect code only for data, actions, permissions, constraints, and states.
   - Do not treat existing JSX, CSS, or layout as a visual reference.

3. **Research concrete patterns**
   - Use current sources.
   - Study interactions and hierarchy, not only aesthetics.
   - Record fit, risks, and applicable principles.

4. **Define UX before styling**
   - Map task, entry/exit, actions, hierarchy, disclosure, errors, desktop, and mobile.
   - Present 2–3 alternatives only for unresolved decisions.
   - Recommend one with trade-offs.

5. **Create low-fidelity artifacts**
   - Use realistic content.
   - Keep alternatives comparable.
   - Do not change approved areas while testing one variable.

6. **Build an isolated prototype when needed**
   - Use local mock data.
   - Keep prototype files outside production code.
   - Make sparse, normal, dense, flagged, error, desktop, and mobile states selectable.

7. **Evaluate in a browser**
   - Capture agreed viewports.
   - Inspect overflow, hierarchy, long content, controls, and state preservation.

8. **Run separate critiques**
   - UX;
   - visual;
   - product fit;
   - accessibility;
   - responsive and long content.

9. **Ask for approval**
   - Summarize approved, rejected, and unresolved decisions.
   - Do not move to high fidelity or production implementation without explicit approval.

## Output contract

Every iteration must provide:

- task and state;
- references or patterns used;
- preserved approved decisions;
- alternatives and trade-offs;
- recommendation;
- artifact paths;
- critique findings;
- unresolved decisions;
- requested user decision.

## Design constraints

- Do not use image generation as the primary UI design method.
- Do not generate UI images unless explicitly requested.
- Avoid generic template-builder aesthetics.
- Avoid a card around every section.
- Avoid decorative recipe-blog styling for productivity products.
- Do not shrink desktop layouts to create mobile designs.
