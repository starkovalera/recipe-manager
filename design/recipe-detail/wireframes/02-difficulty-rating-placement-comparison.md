# U2 Low-Fidelity Comparison — Difficulty and Personal Rating Placement

Status: Resolved through refinement — B2 approved  
Updated: 2026-07-22

## Artifact

- [SVG comparison](./02-difficulty-rating-placement-comparison.svg)

This is a controlled, behavior-and-hierarchy-first comparison. It is not a polished visual direction or production implementation.

## Task and state

Compare two placements in the Default Recipe View header:

1. **Alternative A:** Difficulty and Personal rating sit near the cover and primary recipe metadata.
2. **Alternative B:** Difficulty and Personal rating form one compact row beneath Tags and Collections in the upper-right organization metadata area.

Only placement changes. The comparison uses the same dense imported recipe, content, actions, long title, absent cover, review status, and metadata values.

## Shared realistic scenario

```text
Charred Aubergine, Butter Bean & Preserved Lemon Weeknight Traybake
Instagram video · Marta Cooks · 55 min · 6 servings
No cover available
Difficulty: Moderate
Personal rating: 4.5/5
Collections: Weeknight · Traybakes · +18 (20 total)
Tags: vegan · smoky · +48 (50 total)
3 unresolved imported details
20 ingredients · 10 instructions
```

The approved U1 behavior is fixed: the recipe opens in Default View, a concise status before recipe content links to Import Info, and the persistent `Import info` action remains neutral with no warning icon.

## Preserved approved decisions

- The compact header has a fixed information budget.
- The title remains the strongest element.
- A missing cover must not collapse identity or actions.
- Source and author have no visible field labels and stay inline with time and servings.
- `Cook / Focus` remains primary; `Edit` and `Import info` remain secondary.
- Tags and Collections stay in the upper-right metadata area.
- Both metadata rows show complete visible names plus fixed `+N` disclosure.
- The approved Variant B import-review status stays identical in both alternatives.
- Ingredients and Instructions remain the dominant two-column content.
- Detailed flags remain in Import Info.

## References and principles applied

- Linear issue detail supports protecting the main object identity while grouping mutable or classification-like properties separately.
- Notion database-page layouts support a strict header information budget and selective property prominence.
- Fluent and Carbon tag guidance supports fixed visible item names plus a singular `+N` disclosure action, without turning every value into a decorative pill.

The reusable principle is hierarchy, not source styling: immediate recognition and use take precedence; secondary classification must remain bounded and consistently located.

See `design/recipe-detail/research/pattern-research.md` for current source links, fit, non-fit, and elements that must not be copied.

## Desktop comparison

### Alternative A — Near primary metadata

Difficulty and Personal rating appear directly beneath the inline source/author/time/servings row and before the primary actions.

**Advantages**

- Difficulty is easy to discover while deciding whether to cook.
- Personal rating is visible beside the recipe's immediate use context.
- The two values remain available even if the organization area is collapsed or moved.

**Risks**

- They compete with the title, primary context, actions, and approved review status.
- Personal rating behaves more like organization metadata than a cooking prerequisite.
- Two emphasized values can make the primary region look property-heavy, especially with a long title or absent cover.

### Alternative B — Beneath Tags and Collections

Difficulty and Personal rating share one compact line beneath the bounded Tags and Collections rows.

**Advantages**

- Classification and personal organization metadata remain coherent.
- The title, primary context, actions, and review status keep clearer precedence.
- Dense Tags and Collections use one predictable secondary region rather than expanding both sides of the header.

**Risks**

- Difficulty may be less discoverable at the moment a user decides whether to cook.
- Rating may appear semantically tied to Tags and Collections unless spacing and labeling remain clear.
- On narrow desktop widths, the secondary region must yield before the primary identity region.

## Mobile implications

Mobile uses one deliberate reading order rather than copying desktop coordinates.

- Alternative A places Difficulty and Personal rating between the source/time row and actions. This makes them prominent but delays the primary action and review status.
- Alternative B keeps actions and the approved review status earlier, then groups Collections, Tags, Difficulty, and Personal rating as secondary metadata.
- In both variants, the review status remains before recipe content.
- `+N` disclosure must open an accessible mobile sheet or equivalent inspection surface; editing routes to Organize Recipe.
- If vertical space becomes constrained, organization metadata may collapse as a group, but the recipe title, actions, and review status remain visible.

## Recommendation

Approve **Alternative B: one compact row beneath Tags and Collections**.

Difficulty is useful before cooking, but it is not more important than recipe identity, time, servings, the primary `Cook / Focus` action, or an unresolved-import status. Personal rating is clearly organizational. Keeping both values together avoids splitting closely related management metadata and protects the header's fixed information budget.

If later usability testing shows that users routinely abandon recipes because difficulty is not visible soon enough, elevate Difficulty alone rather than moving both properties into the primary region.

## Accessibility implications

- Do not convey rating solely with star icons; include an accessible numeric value such as `4.5 out of 5`.
- Do not convey Difficulty solely through color.
- Keep Difficulty and Personal rating as distinct accessible values even when visually combined in one row.
- The mobile DOM order must follow the intended reading order rather than desktop visual positioning.
- `+N` remains a named disclosure control with visible focus and a deterministic return target.
- The approved review status precedes uncertain recipe content in keyboard and screen-reader order.

## Dense-data and edge-state coverage

This controlled artifact directly tests:

- S2: an imported recipe with unresolved flags using approved Variant B behavior;
- S3: a long title with no cover;
- S4: 50 Tags and 20 Collections using fixed complete names plus `+N`;
- desktop and mobile header order.

It does not test the full 45–50 ingredient or 35–40 instruction scenario because the decision variable is header hierarchy. Those long-content states remain required for the later isolated prototype.

## Critique findings

### UX

- Alternative A makes Difficulty easier to find but gives Personal rating equal use-level prominence without strong evidence.
- Alternative B creates a clearer primary-versus-secondary model and leaves the cooking action earlier in mobile order.
- Neither alternative should make Default View an editing surface; changes belong in Organize Recipe.

### Visual hierarchy

- Alternative A puts another emphasized row into the most contested area of a dense header.
- Alternative B gives the upper-right area more content, so it needs a strict width and vertical budget.
- The wireframe's boxes and line treatments are schematic and must not become the visual style.

### Product fit

- Difficulty can support a cook/no-cook judgment, while Personal rating primarily supports recognition and organization.
- Keeping them together is simpler, but the two values have somewhat different urgency; later testing should observe whether Difficulty deserves independent elevation.
- Both alternatives preserve the productivity-oriented object-detail direction rather than a decorative recipe-blog header.

### Responsive and long-content

- Alternative B protects the long title by making the organization region yield first.
- Alternative A remains readable in this example but is more likely to wrap or push actions when localized labels are longer.
- On mobile, Alternative B postpones secondary metadata without hiding it; Alternative A delays primary actions.

## Resolution

The upper-right secondary metadata area was selected over the primary metadata placement, then refined in `03-secondary-metadata-order-comparison.md`.

The final approved order is **B2: Difficulty / Personal rating → Collections → Tags**. Prototype and high-fidelity work remain separately gated.
