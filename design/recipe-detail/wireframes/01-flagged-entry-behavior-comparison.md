# U1 Low-Fidelity Comparison — Entry Behavior for Unresolved Import Flags

Status: Approved — Variant B  
Updated: 2026-07-22

## Artifact

- [SVG comparison](./01-flagged-entry-behavior-comparison.svg)

This is a behavior-first low-fidelity artifact. It is not a visual direction, polished UI, or production implementation.

## Task and state

Compare what happens when a user opens an imported recipe:

1. **Control:** no unresolved flags; open ordinary Default Recipe View.
2. **Variant A:** unresolved flags; open Import Info first.
3. **Variant B:** unresolved flags; open Default Recipe View with a concise status linking to Import Info.

The comparison uses one recipe so the entry behavior is the only meaningful variable.

## Shared realistic recipe

```text
Smoky Tomato & Butter Bean Stew
Instagram video · Marta Cooks · 45 min · 4 servings
12 ingredients · 8 instructions · nutrition present
Collections: Weeknight · Pantry
Tags: vegan · smoky · +2
```

The flagged variants share the same unresolved items:

- caption says 35 minutes while the transcript says 45 minutes;
- smoked paprika quantity is uncertain: `1–2 tbsp`;
- one packaging image was ignored.

## Preserved approved decisions

- Default Recipe View remains a reading and usage context.
- Its desktop foundation remains a compact header plus Ingredients/Instructions columns.
- The cover is recognizable but not a hero.
- Source and author use compact inline presentation without visible field labels.
- `Cook / Focus` remains primary; `Edit` and `Import info` remain secondary.
- `Import info` remains neutral and has no warning icon in every state.
- No warning appears when unresolved flags are absent.
- Tags and Collections remain in the upper-right metadata area with fixed `+N` disclosure.
- Detailed flags, provenance, lifecycle controls, and debug data remain in Import Info.
- Import Info uses a desktop result/evidence split and a mobile sequential structure.
- Difficulty and personal-rating placement is not varied in this artifact.

## References and patterns applied

- Linear Triage informed Variant A: review-needed objects can enter a dedicated intake context before normal workflow.
- GitHub pull-request checks informed Variant B: primary object context can remain available while detailed review evidence lives separately.
- Power Query informed the Import Info result-plus-evidence split.
- Apple Books informed explicit return behavior and preservation of location after temporary navigation.

See `design/recipe-detail/research/pattern-research.md` for sources, fit, non-fit, and prohibited copying.

## Desktop behavior

### Control

Opening the recipe lands on Default Recipe View. No warning or status is present. The neutral `Import info` action remains available and opens ordinary Import Info with no review-needed state.

### Variant A — Import Info first

Opening the flagged recipe lands on Import Info. The screen explains that three items need review, keeps the extracted result visible beside evidence, and offers an explicit `View recipe` action.

Browser Back returns to the user's previous location, such as the recipe list. `View recipe` deliberately continues to Default Recipe View. Returning from Default View must not automatically redirect back into Import Info and create a loop.

### Variant B — Default View with status

Opening the flagged recipe lands on Default Recipe View. A concise status sits below the header and links to Import Info. The persistent `Import info` action stays visually neutral and does not absorb warning semantics.

Detailed flags do not appear in Default View. Returning from Import Info restores the same Default View position.

## Mobile behavior

Mobile is not a compressed desktop layout.

- Control opens the ordinary mobile Default View without status treatment.
- Variant A opens a sequential Import Info structure with an explicit `View recipe` action.
- Variant B places the concise status before recipe content and links to sequential Import Info.
- Back, close, and `View recipe` have distinct meanings.
- Navigation must restore the prior recipe position and must not redirect in a loop.

## Alternatives and trade-offs

### Variant A — Open Import Info first

**Advantages**

- The review task cannot be overlooked.
- The reason for uncertainty and relevant evidence are immediately available.
- It matches the approved starting hypothesis and is strongest when flags cross a trust boundary.

**Risks**

- The landing destination may be unexpected.
- Advisory flags may interrupt a recipe that remains usable.
- Users need a clear path to the recipe and must understand why the destination changed.

### Variant B — Default View with concise status

**Advantages**

- Opening a saved recipe remains predictable.
- Users can decide when to inspect import evidence.
- It avoids turning every flag into a gate.

**Risks**

- Users may skip the status and act on uncertain content.
- The status competes with recipe content for attention.
- A warning-heavy treatment could undermine the required neutrality of the persistent action.

## Approved decision

**Variant B is approved.** Opening an imported recipe with unresolved review flags lands on the ordinary Default Recipe View with a concise status and a clear link to Import Info.

The approved behavior is:

- the status appears before recipe content in visual, keyboard, and screen-reader order;
- it states that imported details need review without reproducing detailed flags;
- it links clearly to Import Info;
- the persistent `Import info` action remains neutral and has no warning icon;
- Import Info contains the detailed flags, evidence, and provenance;
- returning from Import Info restores the same Default View position;
- an imported recipe without unresolved flags opens the ordinary Default Recipe View with no status or warning;
- a manual recipe has no Import Info entry point.

Variant A is not the default entry behavior. Review remains visible and actionable without turning every unresolved flag into a gate before recipe use.

## Accessibility implications

- Status meaning must be communicated in text, not color or icon alone.
- The neutral `Import info` action must keep the same accessible name in all states.
- Variant A needs a clear page heading explaining the changed destination.
- `View recipe`, browser Back, and return from Import Info must have predictable, non-looping behavior.
- Variant B's status link must appear before the uncertain recipe content in keyboard and screen-reader order.
- Mobile controls require visible touch targets; gestures cannot be the only exit or navigation method.

## Dense-data and edge-state coverage

This controlled artifact covers S1 and S2 only:

- normal imported recipe with no flags;
- imported recipe with conflicting source information, uncertain quantity, and ignored media;
- desktop and mobile entry/return behavior.

It intentionally does not vary long titles, missing covers, 50 Tags, 20 Collections, long ingredients, or long instructions. Those changes would confound the U1 comparison and belong in subsequent stress-state artifacts or the isolated prototype.

## Critique findings

### UX

- Variant A is clearer about the review task but less predictable as a saved-recipe destination.
- Variant B preserves the familiar destination but depends on users noticing and understanding the status.
- Both require an explicit, non-looping relationship between Default View and Import Info.

### Visual hierarchy

- Variant B introduces another header-level element; later work must prevent it from competing with the title and primary actions.
- Variant A gives Import Info a clear job without adding technical detail to Default View.
- Warning styling is intentionally schematic and must not become the visual direction.

### Product fit

- The decision depends on flag severity semantics that research did not establish.
- Import Info remains useful without flags, but only the flagged state justifies review-first consideration.
- Manual recipes remain outside this comparison because they have no Import Info entry point.

### Responsive and long-content

- Variant A adapts more cleanly to mobile because the review context can become sequential panels.
- Variant B consumes scarce vertical space before mobile recipe content.
- Long-content preservation cannot be fully judged until a browser prototype carries real scroll state.

## Resolution

U1 is resolved in favor of Variant B. Difficulty and personal-rating placement remains separately unresolved and was not part of this decision.

Approved by the user on 2026-07-22. The next low-fidelity decision may compare U2 without changing the approved U1 behavior or any other fixed layout decision.
