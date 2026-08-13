# Shared Product Design Context

## Scope

This directory contains product-design context shared across feature-specific design workspaces.

Editing these documents is a documentation/design action. It does not authorize changes to production application code.

## Content boundary

- Keep only cross-feature working agreements, product scope, workflow, and review criteria here.
- Store feature-specific decisions, scenarios, research, prototypes, and handoff evidence in that feature's `design/<feature>/` workspace.
- Keep each approved behavior in one feature-level source of truth; shared documents must not duplicate screen-specific decisions.
- Preserve decision history in the applicable feature workspace and mark superseded behavior explicitly.
- Promote necessary temporary working material into tracked design artifacts before using it as implementation evidence.
- Mark backend or schema capabilities from prototype mock data for verification during implementation planning.

## Design-to-implementation handoff

Approved UX documents define product behavior, hierarchy, states, and interaction constraints. They do not prescribe copying prototype code or styling into production.

Implementation agents should link exact decision clauses and permanent evidence, verify current application contracts, and implement with production architecture and tests.
