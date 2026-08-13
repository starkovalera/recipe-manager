# Mobile Global Navigation

This isolated iteration preserves the approved Mobile Recipe Detail from Prototype 06 and adds the approved application-level bottom navigation shell. It uses mock data and local SVG assets only and has no production components or APIs.

The global bar contains Recipes, Collections, Notifications, and Profile destinations plus a distinct central Add recipe action. Administration is available from Profile for the admin role. Media, Overflow, Import Info, Add, and deletion sheets share one modal slot and cover the global bar while open.

## Included

- fixed Recipes, Collections, Notifications, and Profile destinations;
- a distinct central Add recipe action with Import and Manual choices;
- Administration inside Profile for the Admin role;
- one modal slot whose sheets cover and disable the global bar;
- sequential Default View with bounded long content;
- Cooking Focus with Ingredients and Instructions tabs;
- compact Tags and Collections disclosure;
- a persistent Media-only bottom sheet and a separate Import Info destination opened from overflow;
- a Media entry for manual recipes even when the media list is empty, with a path to Manage Media;
- a full-width mobile review-status strip when unresolved import flags exist;
- matching accessible review-state dots on Overflow and its Import Info item until all flags are reviewed;
- grouped primary and derived import resources, Ignored resources, and inline irreversible removal confirmations;
- overflow with View / Focus / Edit first, conditional Import Info, Export, and blocking recipe-deletion confirmation;
- normal, flagged, manual, no-cover, dense, long, loading, failed, and missing scenarios;
- User and Debug role differences and mock delete success/failure.

The evaluation toolbar is outside the product surface and changes Scenario, Context, Role, and mock Delete result. Edit is intentionally visible but non-functional and announces `Edit Mode is being designed.` Edit Mode, cover selection, media upload, ingredient editing, checkboxes, and portion scaling remain outside this prototype.

## Run and verify

Open `index.html` directly for review. Run the full browser matrix from the repository root in PowerShell:

```powershell
$env:NODE_PATH='C:\Users\stark\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
& 'C:\Users\stark\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' 'design\recipe-detail\prototypes\10-mobile-global-navigation\test_prototype.js'
```

The stable final markers are `MOBILE_RECIPE_DETAIL_CHECKS_PASS` and `MOBILE_GLOBAL_NAVIGATION_CHECKS_PASS`. The suite covers 360 x 800, 390 x 844, and 430 x 900, all nine scenarios, global destinations, Add, admin placement, modal layering, keyboard/focus behavior, mobile touch targets, sheet dismissal, destructive confirmations, overflow, and broken images.

Capture the deterministic review images with the same runtime and `capture_screenshots.js`. Evidence is under `design/recipe-detail/screenshots/10-mobile-global-navigation/`; the review is under `design/recipe-detail/reviews/10-mobile-global-navigation/`.
