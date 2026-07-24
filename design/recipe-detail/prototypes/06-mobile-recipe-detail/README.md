# Mobile Recipe Detail

This is the complete isolated mobile-first Recipe Detail prototype for reviewing the approved reading and resource-management behavior. It uses mock data and local SVG assets only; it has no production components, APIs, or dependency on Prototype 05.

## Included

- sequential Default View with bounded long content;
- Cooking Focus with Ingredients and Instructions tabs;
- compact Tags and Collections disclosure;
- Media and Import Info in one shared bottom-sheet slot;
- grouped primary and derived import resources, Ignored resources, and inline irreversible removal confirmations;
- overflow and blocking recipe-deletion confirmation;
- normal, flagged, manual, no-cover, dense, long, loading, failed, and missing scenarios;
- User and Debug role differences and mock delete success/failure.

The evaluation toolbar is outside the product surface and changes Scenario, Context, Role, and mock Delete result. Edit is intentionally visible but non-functional and announces `Edit Mode is being designed.` Edit Mode, cover selection, media upload, ingredient editing, checkboxes, and portion scaling remain outside this prototype.

## Run and verify

Open `index.html` directly for review. Run the full browser matrix from the repository root in PowerShell:

```powershell
$env:NODE_PATH='C:\Users\stark\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\stark\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' 'design\recipe-detail\prototypes\06-mobile-recipe-detail\test_prototype.js'
```

The stable final marker is `MOBILE_RECIPE_DETAIL_CHECKS_PASS`. The suite covers 360 × 800, 390 × 844, and 430 × 900, all nine scenarios, keyboard/focus behavior, mobile touch targets, sheet dismissal, destructive confirmations, overflow, and broken images.

Capture the deterministic review images with the same runtime and `capture_screenshots.js`. Evidence is under `design/recipe-detail/screenshots/06-mobile-recipe-detail/`; separate critiques are under `design/recipe-detail/reviews/06-mobile-recipe-detail/`.
