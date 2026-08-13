# Start UI/UX work in Codex

## Repository context

Recipe Manager is a production application repository that also contains isolated product-design workspaces.

Starting a UI/UX task does not make the whole repository design-only. Production development may continue in other branches or worktrees under the root repository instructions.

## Instruction hierarchy

The design context is scoped by path:

```text
AGENTS.md                         Repository-wide production/design routing
design/AGENTS.md                  General non-production design rules
design/shared/AGENTS.md           Shared product-design context rules
design/recipe-detail/AGENTS.md    Recipe Detail design workflow
```

Do not replace the root `AGENTS.md` with a design-only agreement. If importing an updated design package, merge repository-level guidance at the root and keep design-only restrictions in the nested files above.

## Supporting skills

Open PowerShell in the repository root and run, when skill installation or refresh is required:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-ui-ux-skills.ps1
```

Restart Codex after installation. Confirm these skills are visible:

- `product-ui-ux-design`
- `frontend-design`
- `web-design-guidelines`
- `webapp-testing`

The repository-local product-design skill should exist at:

```text
.agents/skills/product-ui-ux-design/SKILL.md
```

## Start a Recipe Detail design task

Read the current Design track and gates first:

```text
design/roadmap.md
```

Open the repository or a dedicated design worktree in Codex. Start with the prompt from:

```text
prompts/01-start-recipe-detail-design.md
```

The task should read the applicable nested instructions and the UI/UX context files before making design changes.

## Expected first deliverable

The first deliverable is research and a structured design brief, not production code and not a polished final screen.

Codex should:

1. read the shared context under `design/shared/` and the Recipe Detail entry points;
2. inspect product code only for functional scope;
3. research current product-interface patterns;
4. identify genuinely unresolved decisions;
5. propose a small number of deliberate next steps.

## Prototype and implementation boundary

Recipe Detail prototype code belongs only under:

```text
design/recipe-detail/prototypes/
```

Design-only tasks must not edit production application code. When a separate task implements an approved design, it should change the appropriate production subtree, use real contracts and tests, and treat prototype code as behavior evidence rather than reusable application code.
