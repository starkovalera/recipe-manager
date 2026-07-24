# Recipe Detail Decision Gallery

Open `index.html` directly in a browser. The gallery is a persistent review surface for the approved global mobile shell, Recipe Detail, and Edit Mode decisions; it is not production UI.

The Global Mobile Shell section links Prototype 10 and records the default top-bar, bottom-navigation, and modal-layer behavior that future mobile screens inherit. Recipe-specific identity, modes, and utilities remain documented separately.

## Update rule

For every newly approved visual decision:

1. capture a readable desktop and/or mobile screenshot under `../../screenshots/`;
2. add a gallery card with its approval status and the structural rule it demonstrates;
3. link the full-size screenshot and any persistent interactive prototype;
4. update the relevant decision document and `docs/ui-ux/07-decisions-log.md`;
5. if the decision replaces an earlier one, keep the old evidence and mark it `Superseded` instead of overwriting it;
6. verify the gallery at 1440 px and 390 px with no horizontal overflow or console errors.

Working Visual Companion files under `.superpowers/` are session evidence. They should not be treated as the consolidated source of truth until their approved state has been captured here and in a decision document.
