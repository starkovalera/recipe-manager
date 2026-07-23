# Responsive and long-content review

Status: pass at tested viewports.

- 1440 px uses a nonmodal equal-width drawer and preserves one auxiliary slot.
- 1280 px and 1024 px use a modal overlay without changing main-menu geometry or producing horizontal overflow.
- 390 px uses separate mode and resource rows plus a full-width bottom sheet.
- Long recipe content remains behind overlays without reflow; closing restores the underlying mode and position.
- Ignored-resource and cascade states remain scrollable within the drawer.
- Recipe deletion remains a centered dialog on desktop and becomes a full-width bottom sheet at 390 px without horizontal overflow.

Evidence: screenshots under `design/recipe-detail/screenshots/05-main-actions-and-responsive-panels/`; automated result `MAIN_ACTIONS_RESPONSIVE_PANELS_CHECKS_PASS`.
