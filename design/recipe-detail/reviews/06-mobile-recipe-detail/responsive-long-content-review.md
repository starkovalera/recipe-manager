# Responsive and long-content review

Status: internal pass; user approval pending.

The automated matrix exercised all nine scenarios at 360 × 800, 390 × 844, and 430 × 900. It checked horizontal overflow, broken images, page errors, console errors, long-title wrapping, and bounded content controls.

- No tested scenario produces document-level horizontal overflow or a broken local image.
- Ingredients start at 12 items, Instructions at 8 steps, and long notes at a four-line preview; each expands and collapses independently.
- Expand/collapse does not reset the page to the top, and Default View scroll is restored after Focus.
- The 360 px no-cover/long-title state keeps both action rows reachable.
- Metadata values wrap within their column; Media and Import Info remain the same mobile width.
- Sheets scroll internally while leaving the underlying reading context in place.

Remaining risk: extreme localization expansion and resource groups substantially larger than the dense mock should receive a later production-content stress pass.
