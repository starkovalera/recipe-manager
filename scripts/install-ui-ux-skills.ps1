$ErrorActionPreference = "Stop"

Write-Host "Installing project-scoped Codex UI/UX skills..." -ForegroundColor Cyan

npx --yes skills add anthropics/skills `
  --skill frontend-design `
  --agent codex `
  --copy `
  --yes

npx --yes skills add vercel-labs/agent-skills `
  --skill web-design-guidelines `
  --agent codex `
  --copy `
  --yes

npx --yes skills add anthropics/skills `
  --skill webapp-testing `
  --agent codex `
  --copy `
  --yes

Write-Host ""
Write-Host "Installed. Restart Codex, then run /skills." -ForegroundColor Green
Write-Host "Expected project skill path: .agents/skills/product-ui-ux-design/SKILL.md"
