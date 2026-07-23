# Supporting Skills for Codex

## Required project skill

Included in this package:

```text
.agents/skills/product-ui-ux-design/SKILL.md
```

Codex scans repository-level `.agents/skills` directories. Restart Codex if it does not appear.

## Recommended external skills

### 1. frontend-design

Purpose: stronger visual direction and avoidance of generic AI interface aesthetics.

Source:

```text
https://github.com/anthropics/skills/tree/main/skills/frontend-design
```

### 2. web-design-guidelines

Purpose: structured web-interface, UX, and accessibility audit after a prototype exists.

Source:

```text
https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines
```

### 3. webapp-testing

Purpose: run local prototypes, capture screenshots, inspect browser behavior, and test responsive states with Playwright.

Source:

```text
https://github.com/anthropics/skills/tree/main/skills/webapp-testing
```

## Installation on Windows

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-ui-ux-skills.ps1
```

The script uses `--copy` to avoid Windows symlink issues.

## Alternative: install inside Codex

Use the built-in installer:

```text
$skill-installer install https://github.com/anthropics/skills/tree/main/skills/frontend-design
$skill-installer install https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines
$skill-installer install https://github.com/anthropics/skills/tree/main/skills/webapp-testing
```

Restart Codex afterward.

## Optional: playwright-interactive

Codex has a curated persistent Playwright skill:

```text
https://github.com/openai/skills/tree/main/skills/.curated/playwright-interactive
```

Install it only when a persistent browser session is valuable.

It currently requires `js_repl` and may require running Codex with reduced sandboxing. Prefer `webapp-testing` unless you understand and accept that environment requirement.

## Existing Superpowers skills

If Superpowers is already installed, use `brainstorming` before a new design area and keep its approval gates.

Do not install large collections of unrelated skills. Too many skill descriptions reduce discovery quality.

## Invocation

Explicit invocation is recommended for design sessions:

```text
Use $product-ui-ux-design and $frontend-design.
```

For prototype review:

```text
Use $product-ui-ux-design, $webapp-testing, and $web-design-guidelines.
```

Project documents and `AGENTS.md` override generic skill preferences.
