# Recipe Manager Repository

## Repository purpose

This repository contains both the production Recipe Manager application and its product-design artifacts.

Production development and UI/UX design may happen concurrently in separate branches or worktrees. A design branch does not redefine the whole repository as a design-only repository, and an implementation branch does not turn prototypes into production code.

## Scope is determined by the task

Before changing files, identify the requested workstream:

- **Application implementation:** production code, APIs, schemas, migrations, tests, infrastructure, or deployment.
- **Product design:** research, decisions, flows, wireframes, screenshots, reviews, or isolated prototypes.
- **Design-to-implementation:** production work that implements an approved design contract.
- **Documentation or maintenance:** repository-wide docs, tooling, or operational changes.

Do not infer the permitted scope from the current branch name alone. Follow the user request, then the nearest applicable `AGENTS.md` for the files being changed.

## Repository map

```text
backend/              Production backend, migrations, and backend tests
frontend/             Production frontend and frontend tests
infra/ docker/        Production infrastructure and deployment support
design/               Product-design context, decisions, evidence, and isolated prototypes
docs/                 Technical documentation, specifications, plans, and runbooks
```

## Global boundaries

- Keep changes within the user-requested workstream and preserve unrelated worktree changes.
- Product-design tasks do not authorize production-code changes unless the user explicitly expands the task to implementation.
- Application tasks may modify production files when required by the request; the former repository-wide design-only prohibition does not apply.
- Never import prototype code, mock data, or prototype styling into production as an implementation shortcut.
- For design-to-implementation work, treat approved decisions and behavior as requirements, then implement them using production architecture, real contracts, accessibility primitives, and tests.
- Existing production UI may be inspected for functional behavior and implementation constraints. For an active redesign, it is not automatically a visual design reference.
- Do not modify Git refs, switch branches, commit, push, or open a PR unless the user has requested the corresponding Git operation.

## Instruction hierarchy

More specific instructions apply automatically within their subtree:

- `design/AGENTS.md` — all non-production design artifacts;
- `design/shared/AGENTS.md` — shared product-design context and decision-document rules;
- `design/recipe-detail/AGENTS.md` — Recipe Detail design workflow and artifact rules;

When a task spans production and design paths, respect both local instruction sets. If they appear to conflict, preserve the design/production boundary and ask before broadening the requested scope.

## Verification

Use checks proportional to the changed workstream:

- production changes: relevant unit, integration, type, lint, and/or end-to-end tests;
- prototype changes: deterministic prototype checks, browser inspection, screenshots, and accessibility/responsive review;
- documentation changes: link, path, consistency, and stale-reference checks.

Report what was verified and what remains unverified.
