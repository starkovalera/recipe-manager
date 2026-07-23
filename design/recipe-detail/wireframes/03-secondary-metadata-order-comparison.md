# U2 Refinement — Secondary Metadata Order

Status: Approved — B2  
Updated: 2026-07-22

## Artifact

- [SVG comparison](./03-secondary-metadata-order-comparison.svg)

This is a new low-fidelity iteration. It preserves the previous U2 artifact and narrows the question to row order inside the upper-right metadata area.

## Task and state

Compare two versions of Alternative B:

1. **B1 — category first:** Collections, Tags, then Difficulty and Personal rating.
2. **B2 — decision signals first:** Difficulty and Personal rating, then Collections and Tags.

Both alternatives keep Difficulty and Personal rating inside the approved secondary metadata area. Neither moves them back into the primary title, source, time, servings, or action region.

## Controlled scenario

Both alternatives use the same dense imported recipe from the previous U2 comparison:

```text
Charred Aubergine, Butter Bean & Preserved Lemon Weeknight Traybake
Instagram video · Marta Cooks · 55 min · 6 servings
No cover available
Difficulty: Moderate
Personal rating: 4.5/5
Collections: Weeknight · Traybakes · +18 (20 total)
Tags: vegan · smoky · +48 (50 total)
3 unresolved imported details
```

## Fixed approved decisions

- The title remains strongest.
- Source, author, time, and servings remain one compact inline row without visible Source or Author labels.
- `Cook / Focus` remains primary; `Edit` and neutral `Import info` remain secondary.
- The approved Variant B import-review status remains identical and precedes recipe content.
- `Import info` has no warning icon.
- Tags and Collections remain bounded with complete visible names and `+N` disclosure.
- Ingredients and Instructions remain unchanged.
- The no-cover and long-title stress state remains unchanged.
- Mobile is a deliberate single-column order, not compressed desktop positioning.

## B1 — Collections and Tags first

Order:

```text
Collections
Tags
Difficulty · Personal rating
```

### Advantages

- Starts with the established organization categories.
- Makes the area read as one classification and organization block.
- Preserves the original Alternative B hierarchy from the previous comparison.

### Risks

- Difficulty appears after two potentially dense disclosure rows.
- A user scanning for cook/no-cook information may overlook it.
- Personal rating and Difficulty can read like a footer to Tags rather than distinct values.

## B2 — Difficulty and Personal rating first

Order:

```text
Difficulty · Personal rating
Collections
Tags
```

### Advantages

- Surfaces the two compact decision signals sooner without moving them into the primary identity region.
- Difficulty is easier to find when deciding whether to cook.
- On mobile, users encounter the short row before the denser `+N` organization rows.

### Risks

- The leading row may receive more visual importance than Tags and Collections.
- Personal rating benefits from the same elevation even though it is less immediately useful than Difficulty.
- The separator and spacing must make the three rows read as one secondary group, not two unrelated blocks.

## Recommendation

Proceed with **B2: Difficulty and Personal rating above Collections and Tags**.

It improves scan order without violating the stronger decision to keep both properties out of the primary title-and-action region. This is a smaller and more proportionate elevation than Alternative A from the previous comparison.

If later evaluation shows that Personal rating does not deserve the same priority, keep the region but test Difficulty first and Personal rating after the organization rows. That third arrangement is not introduced now because the current comparison is intentionally limited to the requested row swap.

## Desktop implications

- Both alternatives use the same fixed-width upper-right area.
- B2 gives a short stable row the first position, followed by two variable-density rows.
- When width is constrained, the secondary area yields before the title and actions.
- `+N` disclosure behavior is identical in both alternatives.

## Mobile implications

- Primary identity, actions, and the approved review status remain above this entire group.
- B1 makes users pass two dense rows before Difficulty and rating.
- B2 exposes the short decision row first, then the organization disclosures.
- The DOM and screen-reader order must match the visible order.
- `+N` opens the same accessible mobile disclosure surface in both alternatives.

## Accessibility implications

- Difficulty must not depend on color.
- Rating must include an accessible numeric value such as `4.5 out of 5`, even if stars are later used visually.
- Difficulty and Personal rating remain distinct accessible values when displayed on one line.
- Separators must not be the only way the values are distinguished.
- Reordering must be implemented in DOM order rather than with CSS-only visual positioning.

## Dense-data coverage

The comparison preserves:

- a long title and absent cover;
- 50 Tags and 20 Collections;
- fixed visible names with `+N`;
- unresolved-import status;
- desktop and mobile reading order.

Full long Ingredients and Instructions remain a later prototype requirement because they do not affect this row-order decision.

## Critique findings

### UX

- B2 makes Difficulty easier to locate without delaying primary actions.
- B1 has a slightly more conventional category-first structure but weaker cook-decision scanning.

### Visual hierarchy

- B2 needs restrained typography so the first secondary row does not compete with the primary metadata.
- B1 risks burying the shortest and potentially most useful row beneath denser information.

### Product fit

- Difficulty supports an immediate cooking judgment; Collections and Tags support organization and rediscovery.
- Personal rating is less urgent, but keeping it paired with Difficulty respects the approved U2 comparison scope.

### Responsive and long-content

- B2 is more efficient on mobile because the short stable row appears before variable-density disclosures.
- Neither order may increase the metadata area's fixed height when Tags or Collections grow.

## Resolution

**B2 is approved:** Difficulty / Personal rating → Collections → Tags.

The three rows remain one secondary metadata group in the upper-right area. Difficulty and Personal rating lead the group but do not move into the primary title, source/time/servings, or action region.

Approved by the user on 2026-07-22. U2 is resolved; prototype and high-fidelity work remain separately gated.
