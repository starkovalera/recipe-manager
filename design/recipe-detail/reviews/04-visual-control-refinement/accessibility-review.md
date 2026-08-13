# Accessibility Review — Visual-Control Refinement

Status: Browser-checked at low fidelity  
Updated: 2026-07-23

- Icon-only cross, trash, overflow, and external-link controls have distinct accessible names or link text; decorative SVGs are hidden from assistive technology.
- Icon hit targets are at least 40 px and retain visible `:focus-visible` styling.
- Cascade confirmation uses `alertdialog`, focuses Cancel, supports Escape, and communicates consequences in text rather than color alone.
- External links are semantic anchors, open separately, and use `noopener noreferrer`.
- Drawers contain overscroll and tablet/mobile backgrounds remain inert.

High fidelity must recheck 44 px mobile targets, final contrast, tooltip behavior, browser zoom, and announcement wording.
