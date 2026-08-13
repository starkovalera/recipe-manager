# Recipe Detail Functional Scope

This file records functional design inputs, not visual requirements. Current production code may be inspected to verify these capabilities, but its appearance is not a design reference.

## Recipe data

A recipe may include:

- title;
- source platform or source type;
- source or author label;
- cover image;
- alternative imported images;
- servings;
- cooking time;
- ingredients;
- ordered instructions;
- cooking notes;
- estimated nutrition;
- tags;
- collections;
- rating;
- difficulty;
- cuisine;
- meal type;
- dietary attributes;
- other search and management metadata.

An imported recipe may also include:

- source URLs;
- imported text;
- imported images;
- parent-child relationships between imported materials;
- used, ignored, and deleted source states;
- review flags;
- extraction or provenance information;
- debug information visible only to eligible roles.

## User tasks

Users may need to:

- read a recipe;
- start a focused cooking view;
- scale portions;
- temporarily check ingredients and steps;
- inspect optional cooking media;
- edit recipe content;
- organize the recipe;
- choose a cover;
- inspect import information and provenance;
- resolve or understand import warnings;
- delete or restore imported materials where permitted;
- perform rare or destructive recipe actions.

These tasks must not be combined into one permanent page.

## Design boundary

The current design project covers Recipe Detail information architecture and related contexts. Product-wide patterns discovered here must be recorded explicitly before reuse by other screens.

## Deferred scenarios

Detailed design is deferred for:

- nutrition calculated from actual products and weights used during a cooking session;
- cooking batches or persistent cooking sessions;
- cooked dish weight;
- nutrition per actual cooked portion;
- consumption tracking;
- automatic step-level media association.
