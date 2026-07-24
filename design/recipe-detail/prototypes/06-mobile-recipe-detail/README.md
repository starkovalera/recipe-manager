# Mobile Recipe Detail — Task 1 shell

This is an isolated, mobile-first design prototype for Recipe Detail. It uses local mock data and local SVG assets only; it has no production components, APIs, or runtime dependency on Prototype 05. Production code remains out of scope.

The toolbar is intentionally outside the simulated product surface and switches Scenario, Context, Role, and mock Delete result. Task 1 establishes the shell, all nine scenario records, and the browser smoke test. Edit Mode remains an explicit non-functional boundary for later work.

Run the smoke test from the repository root in PowerShell:

```powershell
$env:NODE_PATH='C:\Users\stark\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\stark\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' 'design\recipe-detail\prototypes\06-mobile-recipe-detail\test_prototype.js'
```

The expected Task 1 marker is `TASK_1_MOBILE_RECIPE_DETAIL_SMOKE_PASS`.
