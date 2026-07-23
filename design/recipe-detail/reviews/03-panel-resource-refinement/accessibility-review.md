# Accessibility Review — Panel and Resource Refinement

Status: Browser-checked at low fidelity  
Updated: 2026-07-23

- Thumbnail buttons expose descriptive preview/collapse names and expanded state; decorative thumbnail images have empty alt text while the expanded image is named.
- Inline cascade confirmation uses `alertdialog`; safe Cancel receives focus and Escape cancels without closing Import Info.
- Affected rows communicate `Will be removed` or `Kept as cover` in text in addition to background color.
- The shared slot exposes a named Media / Import Info navigation control and never creates two dialogs.
- Tablet and mobile keep the parent context inert and trap focus inside the current drawer/sheet.

High fidelity must verify 44 px icon targets, final contrast, zoom behavior, and screen-reader announcements after destructive completion.
