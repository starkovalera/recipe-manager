# Recipe Manager Product Scope for Design

## Purpose of this file

This file describes functional scope only.

It must not be used to reproduce the current frontend appearance.

## Product summary

Recipe Manager is a productivity application for importing, storing, reviewing, editing, organizing, finding, and using recipes.

The broader product includes:

- recipe import from text, images, and supported links;
- asynchronous import jobs;
- recipe list and detail views;
- recipe editing;
- recipe collections;
- tags and search metadata;
- notifications;
- different capabilities for ordinary, debug, and administrative roles.

## Recipe Detail functional scope

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

## User tasks in the Recipe Detail area

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

## Design-scope boundary

The current design project covers the Recipe Detail information architecture and its related contexts.

Global navigation may be represented as a neutral shell, but redesigning the whole application navigation is not part of the first Recipe Detail iteration.

## Product-code inspection rule

When inspecting the repository, extract only:

- names and meanings of data fields;
- available actions;
- permissions;
- validation constraints;
- state transitions;
- business invariants;
- error and loading cases.

Do not extract visual hierarchy or layout from current JSX or CSS.

## Explicitly deferred

Do not design detailed flows for:

- nutrition calculated from actual products and weights used during a cooking session;
- cooking batches or persistent cooking sessions;
- cooked dish weight;
- nutrition per actual cooked portion;
- consumption tracking;
- automatic step-level media association.
