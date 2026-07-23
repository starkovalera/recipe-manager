# Realistic Data and Stress Scenarios

Use these scenarios in wireframes and prototypes.

Do not evaluate only a short, ideal recipe.

## S1 — Normal imported recipe

- medium title;
- cover present;
- source and author present;
- 12 ingredients;
- 8 steps;
- 4 tags;
- 2 collections;
- nutrition present;
- no review flags.

## S2 — Imported recipe with unresolved flags

- conflicting source information;
- ignored media;
- uncertain time or quantity;
- neutral `Import info` action;
- either default entry into Import Info or a concise warning on Default View.

## S3 — Long title and no cover

- title wraps to 2–3 lines;
- default image or empty-cover treatment;
- primary actions remain reachable;
- metadata does not collapse unpredictably.

## S4 — Dense organization metadata

- 50 tags;
- 20 collections;
- several dietary attributes;
- collapsed header representation with fixed visible length and `+N`;
- expanded state via popover, sheet, or dedicated organization context.

## S5 — Long ingredients

- 45–50 ingredients;
- long quantities and units;
- grouped ingredients if supported;
- long ingredient notes;
- easy scanning without card repetition.

## S6 — Long instructions

- 35–40 steps;
- several multi-paragraph steps;
- stable numbering;
- readable line length;
- no loss of current position.

## S7 — Long cooking notes

- multiple paragraphs;
- warnings and substitutions;
- optional collapse only if discoverable and useful.

## S8 — Variable nutrition

Test:

- complete values;
- partial values;
- missing values;
- clearly estimated values;
- long labels and different units.

## S9 — Multiple sources and media

- original URL;
- extracted text;
- several used images;
- ignored images;
- deleted and restorable resources;
- source hierarchy;
- optional debug data for an eligible role.

## S10 — Manual recipe

- no imported resources;
- no `Import info` action;
- normal Default Recipe View.

## S11 — Mobile cooking

- one-handed use;
- Ingredients/Instructions switching;
- checked states;
- long step;
- media bottom sheet;
- return to exact scroll position.

## S12 — Errors and loading

- loading recipe;
- failed recipe load;
- missing recipe;
- failed save;
- failed resource action;
- empty collections;
- no tags;
- unavailable media.
