# Mobile Edit Save-Action Comparison

Status: option 1 approved on 2026-07-25

This static iteration preserves the selected always-compact mobile Recipe header and compares only two ways to remove the heavy `Cancel / Save changes` bar:

1. `Save` in the top toolbar, with Media moved to Overflow;
2. a lightweight dirty-state accessory above unchanged global navigation.

Both use Back as the exit action. When the Recipe Edit draft is dirty, Back must open the unsaved-changes guard. The global bar remains navigation-only and the editor stays within Recipes.

## Approved direction

Use option 1: `Save` in the compact top toolbar. Media and Import Info move to Overflow while Edit is active. Do not continue the bottom-accessory alternative.

Evidence is stored under `../../screenshots/edit-mode/12*.png`.
