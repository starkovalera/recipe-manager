# Recipe Manager Product Scope for Design

## Purpose

This file describes product capabilities that may inform multiple feature-design workspaces. It must not be used to reproduce the current frontend appearance.

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

## Product-code inspection rule

When inspecting the repository for design work, extract only:

- names and meanings of data fields;
- available actions;
- permissions;
- validation constraints;
- state transitions;
- business invariants;
- error and loading cases.

Do not extract visual hierarchy or layout from current JSX or CSS.

Feature-specific data, tasks, scenarios, and deferred behavior belong in the applicable `design/<feature>/` workspace.
