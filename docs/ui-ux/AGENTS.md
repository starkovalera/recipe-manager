# UI/UX Documentation Instructions

## Scope

This directory contains durable UI/UX source-of-truth documentation shared by design and future implementation work.

Editing these documents is a documentation/design action. It does not authorize changes to production application code.

## Decision discipline

- Record approved behavior explicitly and distinguish it from proposals, historical comparisons, and unresolved questions.
- Preserve decision history. Mark superseded behavior instead of silently removing the reason a later decision exists.
- Keep broad summaries aligned with the detailed decisions and permanent prototype evidence.
- When Recipe Detail documents conflict, the later explicit entry in `07-decisions-log.md` wins.
- Do not use temporary `.superpowers` files as durable evidence; promote necessary content into tracked decisions, prototypes, screenshots, and reviews.
- Do not invent backend or schema capabilities from prototype mock data. Mark them for verification during implementation planning.

## Design-to-implementation handoff

Approved UX documents define product behavior, hierarchy, states, and interaction constraints. They do not prescribe copying prototype code or styling into production.

Implementation agents should link exact decision clauses and permanent evidence, verify current application contracts, and implement with production architecture and tests.
