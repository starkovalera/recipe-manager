# Global Mobile Application Shell

Status: approved

Approved: 2026-07-24

Applies to: all mobile Recipe Manager screens

## Decision

Mobile screens use one consistent application shell:

- a hierarchy-aware sticky top bar;
- a fixed global navigation bar on ordinary application pages;
- one modal sheet layer that opens above and fully covers the global navigation;
- focused creation or task flows that temporarily replace the ordinary shell.

The shell is a product-wide default. Screen-specific identity, modes, and contextual actions plug into it; Recipe Detail geometry and labels are not copied onto unrelated screens.

## Top bar

### Root destinations

Root screens such as Recipes, Collections, Notifications, and Profile do not show Back.

- Expanded: screen title plus only the contextual actions needed by that destination.
- Compact after scroll: one sticky row with the title and the same essential contextual actions.
- Search belongs inside Recipes rather than in the global navigation.

### Nested and detail screens

Nested screens show an icon-only Back action at the left edge.

- Expanded: a utility row, then the screen identity or summary, then optional local modes.
- Compact after scroll: one sticky row with Back, a truncated title, and only essential contextual utilities.
- The title truncates before controls are compressed or pushed off-screen.
- Local modes may move into Overflow in the compact state when they cannot remain visible without crowding.

### Approved Recipe Detail instance

- Expanded utility row: Back on the left; Media and Overflow on the right.
- Identity area: compact cover, recipe title, neutral source/author line when available, then cooking facts.
- Local modes: `View / Focus / Edit` in a separate row below identity.
- Compact row: Back, truncated recipe title, Media, Overflow.
- Manual recipes keep Media because it is also the path to upload images. Only Import Info is conditional on import history.
- When review flags exist, Overflow and its `Import info` item repeat the same notification dot.

Approved visual evidence: [`mobile-header-expanded-compact-approved.png`](../screenshots/mobile-shell/mobile-header-expanded-compact-approved.png).

## Global bottom navigation

The stable order is:

```text
Recipes | Collections | Add | Notifications | Profile
```

- Recipes and Collections are separate, equal-priority destinations.
- Add is a visually distinct central action, not a selected destination. It opens a compact chooser for Import recipe and Create manually.
- Notifications is a top-level destination.
- Profile is always present. Administration appears inside Profile for eligible roles, so role changes never alter global navigation geometry.
- The active destination follows the application hierarchy. Recipe Detail remains within Recipes.
- Page content reserves the navigation height and device safe area so the final content is never obscured.

## Sheets and focused flows

- Add, Media, Overflow, Import Info, metadata disclosure, and destructive confirmations use one modal-layer slot.
- A modal sheet opens above and fully covers the global navigation. Covered navigation is neither clickable nor available to accessibility navigation.
- Moving from Overflow to Import Info or Delete replaces the current sheet; sheets do not stack.
- Closing a sheet returns to the same mode, scroll position, selected item, and safe draft state.
- Mobile sheets support swipe-down dismissal when safe and always retain an explicit close icon.
- Import and Manual Create are focused full-screen flows without global navigation. Back or Cancel owns exit and dirty-draft protection.

## Default and exceptions

Use the global top and bottom shell on ordinary pages, including Recipe Detail View, Focus, and Edit. Hide or replace the bottom bar only for a focused full-screen task whose exit and unsaved-state behavior is explicit.

Do not add screen-specific utilities to the global bottom bar. Do not add Back on root destinations. Do not keep the global bar visible beneath an active modal sheet.

## Accessibility contract

- Icon-only controls have meaningful accessible names and at least a 44 by 44 CSS pixel target.
- Notification dots are accompanied by accessible state text and never carry meaning alone.
- Focus moves into an opened sheet and returns to the invoking control after dismissal.
- Back behavior is predictable: it closes the top modal layer first, then leaves the nested screen.
- Reduced-motion preferences must not remove state-change clarity.

## Product-wide reuse

This is the default mobile shell for future screen design. Each new screen must specify:

1. whether it is a root, nested/detail, or focused-task screen;
2. its expanded identity/title content;
3. the essential actions that survive in the compact top bar;
4. its active global destination;
5. whether any action opens the shared modal sheet slot.

Visual styling remains low fidelity; the information hierarchy and interaction contract are approved.
