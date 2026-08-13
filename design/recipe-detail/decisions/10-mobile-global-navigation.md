# Mobile Global Navigation — Approved Direction

## Status

Approved on 2026-07-24 for the mobile application shell.

## Navigation model

Use a persistent bottom application bar with four top-level destinations and one visually distinct central creation action:

```text
Recipes   Collections      +      Notifications   Profile
```

- `Recipes` and `Collections` remain separate, equal-priority destinations.
- Search belongs inside `Recipes`; it is not a global navigation destination.
- The central `+` is an action rather than a selected navigation destination. It opens a compact chooser for `Import recipe` and `Create manually`.
- `Notifications` is a top-level destination and may use a restrained unread badge.
- `Profile` is a top-level destination.
- Eligible users reach `Administration` from Profile. Admin never adds or removes a global-bar position.

## Modal-layer rule

The global bar is visible on ordinary application pages in every Recipe Detail mode. Any modal sheet opens above and completely covers the global bar while the sheet is active. The covered bar is neither visible nor interactive.

This rule applies to:

- Media;
- recipe overflow actions;
- Import Info;
- the Add chooser;
- recipe deletion confirmation;
- metadata disclosures and other modal mobile sheets.

Only one modal-layer slot exists. A transition such as Overflow to Import Info or Overflow to Delete replaces the current sheet instead of stacking another sheet above it. Dismissing the active sheet returns to the same page, mode, and scroll position.

Selecting `Import recipe` or `Create manually` closes the Add chooser and enters a focused full-screen creation flow. The global bar remains hidden in that flow; Cancel or Back handles exit and any dirty-draft protection.

## Accessibility and layout constraints

- Each destination has an icon and visible text label.
- The central Add action has the accessible name `Add recipe` and no selected-tab semantics.
- The current destination is exposed semantically as current.
- Touch targets remain at least 44 CSS pixels where practical.
- Page content reserves the bar plus device safe-area inset so the final content is never obscured.
- Modal sheets own focus while open and restore focus to their trigger when dismissed.
- Swipe dismissal always has an equivalent visible close control.

## Prototype scope

Prototype 10 validates the shell on the approved mobile Recipe Detail without redesigning Recipe Detail content. It must show:

1. the ordinary fixed global bar;
2. the Add chooser covering the bar;
3. Media covering the bar;
4. Overflow covering the bar;
5. Import Info replacing Overflow in the single modal slot;
6. Profile with an Administration entry for an admin role only.

Production implementation and full Recipes, Collections, Notifications, Profile, Admin, Import, and Manual Create screens remain out of scope.
