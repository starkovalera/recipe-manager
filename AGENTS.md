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

## Agent skills

### Issue tracker

Issues and specs for this repo live as GitHub issues; use the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The repo uses the default five canonical triage labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo with root `CONTEXT.md` and `docs/adr/`. See `docs/agents/domain.md`.

### Planning

Start project planning from `docs/roadmap.md`. Active issues follow the `[DESIGN]` / `[DEV]` title convention and native blocker rules in `docs/agents/planning.md`.

### Future-work TODO shorthand

When the user says “добавь в todo”, “добавь в туду”, or “add to todo”, record the item in the matching canonical document under [`docs/future/`](docs/future/README.md). Preserve the document's funnel stage and enough context to support later refinement. Use the existing capability files first: `import-and-ai.md`, `operations-and-lifecycle.md`, `product-expansion.md`, `list-and-review-ux.md`, `search-evolution.md`, or `youtube-video-import.md`; if no file fits, create a new capability document and add it to `docs/future/README.md`. The umbrella refinement and prioritization task is [#33](https://github.com/starkovalera/recipe-manager/issues/33). Treat this shorthand as a documentation capture request; create or update a GitHub issue only when the user separately asks for a task or an explicit refinement decision promotes the item under `docs/agents/planning.md`.

### Task completion

Development tasks use the shared completion checkpoint in `docs/agents/task-completion.md`. Backend tasks must run its refactoring review before handoff.
