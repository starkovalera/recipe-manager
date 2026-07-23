# Recipe Detail Structure-Validation Prototype

Status: Browser-evaluated; proposed for user approval  
Updated: 2026-07-22

This is an isolated, dependency-free, low-fidelity prototype. It uses mock data and has no connection to production components, APIs, routes, or styles.

## Start

From this directory:

```powershell
python -m http.server 4173 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:4173
```

The automated test runner starts its own dependency-free Node HTTP server because the bundled Python runtime in this workspace accepted the test port but returned empty HTTP responses. No package download is required.

## Evaluation controls

Use the toolbar to switch:

- scenario: normal, flagged, manual, dense, long, loading, failed, or missing;
- context: Default View, Import Info, or Cooking Focus;
- role: ordinary user or debug-eligible user.

The prototype tests structure and interaction only. Typography, colors, borders, spacing, iconography, and imagery are not a high-fidelity visual direction.

## Verification

Automated browser checks cover normal, flagged, manual, dense, long, loading, failed, missing, Import Info, debug role, resource-action error, disclosure focus return, Cooking Focus state preservation, drawer/sheet semantics, and mobile overflow.

Evidence:

- screenshots: `design/recipe-detail/screenshots/01-structure-validation/`;
- separate reviews: `design/recipe-detail/reviews/01-structure-validation/`;
- test runner: `test_prototype.js`.
