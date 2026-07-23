# Start UI/UX work in Codex

## 1. Copy this package

Copy all files from this package into the root of the `recipe-manager` repository.

The result should include:

```text
AGENTS.md
.agents/skills/product-ui-ux-design/
docs/ui-ux/
design/recipe-detail/
prompts/
scripts/
```

If the repository already contains an `AGENTS.md`, merge the sections rather than deleting unrelated project instructions.

## 2. Install supporting skills

Open PowerShell in the repository root and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-ui-ux-skills.ps1
```

Restart Codex after installation.

## 3. Verify skills

In Codex:

```text
/skills
```

Confirm that these are visible:

- `product-ui-ux-design`
- `frontend-design`
- `web-design-guidelines`
- `webapp-testing`

If `product-ui-ux-design` is missing, verify this exact path:

```text
.agents/skills/product-ui-ux-design/SKILL.md
```

## 4. Start a new Codex thread

Open the repository root in Codex. Start with the prompt from:

```text
prompts/01-start-recipe-detail-design.md
```

## 5. Expected first deliverable

The first deliverable is research and a structured design brief, not production code and not a polished final screen.

Codex should:

1. read the UI/UX context files;
2. inspect product code only for functional scope;
3. research current product-interface patterns;
4. identify unresolved decisions;
5. propose a small number of deliberate next steps.

## 6. Prototype boundary

When HTML/CSS mockups begin, they must live only under:

```text
design/recipe-detail/prototypes/
```

Do not allow Codex to edit `frontend/src` during this phase.
