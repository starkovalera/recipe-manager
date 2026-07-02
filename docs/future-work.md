# Future Work and Cleanup Notes

This document tracks known follow-up work, shortcuts, compatibility leftovers, and intentional deferrals that should not be forgotten after phase/subphase completion.

After each completed phase or subphase, review the finished work and propose candidate items to add here before moving on.

## AI and Import Pipeline

- Remove `sourcePosition` and `crop` from the Pydantic AI response schema for `coverCandidate`. They are currently kept as `None`-only legacy compatibility fields after the OpenAI response schema was narrowed to `sourceRef` and `confidence`.

## Tags

- Validate tag name and tag description length on both frontend and backend.
- Show user-facing errors when creating a duplicate tag or exceeding the configured tag limit.
- Show a recipe-count badge/counter next to each tag.
- Add a way to navigate from a tag to the list of recipes containing that tag.
- Add pagination for tag management.
- Add tag sorting options.
- Add quick tag search/autocomplete by tag name.

## Ingredients

- Validate ingredient field lengths on both frontend and backend when editing recipes.
