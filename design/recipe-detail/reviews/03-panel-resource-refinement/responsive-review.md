# Responsive Review — Panel and Resource Refinement

Status: Browser-checked at 1440 × 900, 1024 × 768, and 390 × 844  
Updated: 2026-07-23

- Wide desktop reallocates space to one auxiliary drawer; expanded Media may use a wider version of the same slot.
- At 1024 px, the shared slot overlays the unchanged Cooking Focus and switches content without stacking another panel.
- At 390 px, the same state model becomes a bottom sheet. The Media / Import Info switch stays reachable at the top of the sheet while content scrolls below it.
- Image rows retain thumbnails and parent/child connectors without horizontal overflow.
- Corrected B moves actions to a full header row on mobile rather than squeezing them beneath the small cover.

High fidelity should additionally check 320 px width, localized labels, safe-area insets, and very long resource names.
