# Accessibility review

Status: pass for prototype scope.

- Icon-only controls have accessible names and visible focus states.
- Modal desktop overlays and mobile sheets make the background inert and trap keyboard focus.
- Escape closes a panel; Escape first cancels a pending destructive confirmation.
- The mobile sheet retains a cross so swipe is never the sole dismissal method.
- Swipe begins only on the visible handle, and reduced-motion preference disables the return animation.
- Current web-interface guideline audit added a keyboard skip link, explicit tap feedback, safe-area padding, lazy below-fold thumbnails, and balanced headings.
- Secondary deletion confirmation receives focus, supports Cancel and Escape, announces successful removal, and never relies on color alone.
- Recipe deletion traps focus in a named modal, supports cross/Cancel/Escape, exposes text in addition to danger color, and reports failure with `role="alert"`.
