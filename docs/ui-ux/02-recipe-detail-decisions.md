# Recipe Detail UX Decisions

Updated: 2026-07-22

This file is the source of truth for agreed Recipe Detail UX structure, including decisions made during UX Pilot exploration.

## Core principle

Recipe Detail supports several distinct user tasks.

Do not combine them into one long page, one permanently visible form, or one overloaded dashboard.

## Information architecture

```text
Recipe
├── Default Recipe View
├── Cooking Focus
│   └── Optional Media
├── Import Info
├── Edit Recipe Content
├── Organize Recipe
└── Cover Picker
```

## 1. Default Recipe View

### Purpose

The default view is primarily for reading and using a saved recipe.

### Approved desktop structural foundation

Use a compact header followed by a productivity-oriented two-column reading layout:

- fixed-width Ingredients column on the left;
- wider Instructions column on the right;
- Estimated Nutrition below Ingredients;
- Cooking Notes below Instructions.

Ingredients and Instructions are the dominant content.

Do not wrap every section in a large card.

### Header content

The header contains:

- a moderately sized, recognizable cover image;
- recipe title as the strongest element;
- compact primary recipe metadata;
- page actions;
- compact secondary organization metadata.

The cover must not become a large hero image.

### Source and author presentation

Do not show visible field labels such as `Source` and `Author` in the default reading view.

Use a compact inline presentation, for example:

```text
Instagram video · Marta Cooks · 30 min · 4 servings
```

Source and author must remain distinguishable through separators, typography, icons, or spacing.

### Main actions

For imported recipes, show:

```text
Cook / Focus · Edit · Import info · Overflow
```

- `Cook / Focus` is primary.
- `Edit` is secondary.
- `Import info` is a neutral secondary action.
- Rare or destructive actions belong in overflow.

### Import Info availability and review flags

`Import info` is available for every imported recipe, even when no review flags exist.

Do not put a warning icon inside the neutral `Import info` action.

When no unresolved review flags exist:

- open the ordinary Default Recipe View by default;
- show `Import info`;
- do not show a warning banner.

When unresolved review flags exist, two behaviors remain valid for design comparison:

1. **Preferred behavior:** open Import Info by default.
2. **Fallback behavior:** open Default Recipe View with a concise warning/status and a clear link to Import Info.

In either behavior:

- the `Import info` action remains neutral;
- detailed flags, provenance, debug data, and source lifecycle controls remain outside the Default Recipe View.

### Tags and collections

Place Tags and Collections in a compact metadata area in the upper-right part of the header, visually separate from the cover and primary metadata.

Large numbers must be collapsed to a stable fixed length.

Example:

```text
Collections: Weeknight · Pasta · +3
Tags: vegetarian · one-pan · quick · +7
```

Requirements:

- show a limited number of visible items;
- use `+N` or equivalent progressive disclosure;
- keep header height stable;
- do not create a large tag cloud;
- do not let metadata displace the title or primary actions.

### Difficulty and personal rating

This placement is unresolved and must be evaluated through two otherwise identical variants:

- **Alternative A:** difficulty and rating near the cover and primary recipe metadata;
- **Alternative B:** difficulty and rating in one compact row under Tags and Collections in the upper-right metadata area.

Do not change other layout decisions while comparing these variants.

### Secondary metadata

The following may be available compactly but must not compete with the recipe:

- tags;
- collections;
- personal rating;
- difficulty;
- cuisine;
- meal type;
- dietary attributes;
- other search and management metadata.

### Must not remain visible on this page

- source lifecycle controls;
- detailed review flags;
- debug information;
- provenance details;
- imported-resource statuses;
- resource IDs;
- full edit forms;
- source deletion and restoration actions.

## 2. Import Info

### Purpose

Import Info is a separate working context for inspecting the imported result, its provenance, source quality, and technical information.

It is not only an error-resolution screen. It remains useful when no review flags exist.

### Availability

The context is reachable from the neutral `Import info` action for every imported recipe.

### Contents

It may include:

- imported recipe result;
- source URLs;
- imported text and images;
- used, ignored, and deleted sources;
- review flags when present;
- debug information for eligible roles;
- source and author corrections;
- source deletion and restoration;
- information about which materials were used or ignored during extraction.

### Preferred layout

Use a split-view interface on desktop:

- extracted recipe result on one side;
- sources, flags, provenance, and debug information on the other.

On mobile, use sequential panels, tabs, or another mobile-specific structure rather than compressed desktop columns.

### Exclusions

Do not make these primary tasks in Import Info:

- cover selection;
- recipe organization;
- cooking-focused presentation.

## 3. Edit Recipe Content

Editing recipe content is separate from organization metadata.

It includes:

- title;
- source and author;
- cover entry point;
- servings;
- cooking time;
- ingredients;
- instructions;
- notes;
- estimated nutrition.

Avoid one uninterrupted long form.

Ingredients and steps must support adding, editing, deleting, and reordering.

Do not expose source lifecycle management, review flags, provenance, or debug data.

## 4. Organize Recipe

Organization is a separate section or screen for:

- tags;
- collections;
- personal rating;
- difficulty;
- cuisine;
- meal type;
- dietary attributes;
- other search and management properties.

It must not become a continuation of one very long recipe-content form.

## 5. Cover Picker

Cover selection and source review are separate tasks.

Show only:

- current cover;
- available images;
- selected image;
- use as cover;
- upload custom image;
- future crop or position controls when needed.

Do not expose:

- debug information;
- resource IDs;
- source lifecycle statuses;
- source deletion or restoration.

## 6. Cooking Focus

Cooking Focus is a simplified recipe view, not a separate complex cooking system.

### Visible by default

- compact recipe title;
- servings;
- portion scaling;
- ingredients;
- instructions;
- cooking notes;
- exit focus action.

Estimated nutrition may remain compactly available but is not central.

### Hidden

- large cover image;
- source and author;
- tags and collections;
- rating and classifications;
- review flags;
- debug information;
- administrative actions;
- source management.

### Interactions

- temporary ingredient checkmarks;
- temporary completed-step states;
- easy Ingredients/Instructions switching on mobile;
- keep-screen-awake support when technically possible;
- return to the full recipe without losing reading position.

Temporary cooking state does not need to persist after leaving the mode in the first version.

## 7. Optional Media in Cooking Focus

Show `Media · N` only when media exists.

Media is closed by default.

### Desktop

Open a right-side drawer while keeping Ingredients and Instructions visible.

Opening or closing must not reset:

- ingredient checks;
- completed steps;
- scroll position.

### Mobile

Open a bottom sheet that may expand upward.

Closing returns to the same recipe position.

### Contents

Show:

- image thumbnails;
- enlarged preview;
- image origin or short caption;
- external links;
- source platform;
- author or source label;
- current-cover marker when useful.

Do not show:

- resource IDs;
- technical statuses;
- extraction flags;
- debug data;
- source deletion or restoration.

Present links as understandable actions rather than raw URLs.

Embedded video is not required for the first version.

## Deferred

- nutrition based on actual cooking products and weights;
- cooking batches and persistent sessions;
- cooked dish weight;
- nutrition per actual portion;
- consumption tracking;
- step-level image association.
