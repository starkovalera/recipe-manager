# UI/UX Review Checklist

## UX review

- Is the current screen optimized for one primary task?
- Are separate tasks kept in separate contexts?
- Is the primary action obvious?
- Are rare and destructive actions de-emphasized?
- Does progressive disclosure reduce noise without hiding necessary actions?
- Can users predict where actions lead?
- Are entry, cancel, back, and exit behaviors clear?
- Are review and error states actionable?

## Visual review

- Is information hierarchy visible before reading labels?
- Is useful information denser than decorative space?
- Are sections separated without placing every section in a card?
- Are shadows, radii, chips, and accent colors restrained?
- Does the interface look like a productivity product rather than a recipe blog?
- Does any metadata compete with the title, ingredients, or instructions?
- Are variants structurally different rather than recolored copies?

## Product-fit review

- Does the design support imported and manual recipes?
- Is Import Info useful even without flags?
- Is debug or provenance information restricted to the correct context?
- Are content editing and organization separated?
- Is cover selection isolated from source lifecycle controls?
- Is Cooking Focus simplified rather than expanded into a new system?

## Accessibility review

- Is keyboard order logical?
- Are focus indicators visible?
- Do controls have clear accessible names?
- Is status information conveyed without color alone?
- Are warning and destructive actions distinguishable?
- Are drawers, dialogs, popovers, and bottom sheets correctly structured?
- Is text readable at browser zoom?
- Are touch targets appropriate on mobile?

## Responsive and long-content review

- Is mobile designed intentionally rather than as a shrunken desktop?
- Do long titles preserve actions?
- Do 50 tags and collections remain controlled?
- Do 50 ingredients and 40 steps remain navigable?
- Do overlays preserve scroll and temporary state?
- Do columns stack in a meaningful order?
- Are sticky controls used only when they improve the task?
- Is horizontal overflow avoided?

## Approval checklist

Before marking a design approved:

- approved decisions are documented;
- rejected variants are retained with reasons;
- unresolved decisions are explicit;
- normal, dense, flagged, error, and mobile states were reviewed;
- no production code was changed;
- user approval was obtained.
