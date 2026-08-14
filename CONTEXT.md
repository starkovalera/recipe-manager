# Recipe Manager

Recipe Manager is a product for importing, organizing, reviewing, editing, finding, and using recipes across web and mobile clients.

## Release sequencing

**V1 — Web Release**:
The first production release is web-only. V1 includes the complete approved
responsive-web product experience, the shared contracts it needs, production
operations, and the web release gates. A mobile client is not a V1 blocker or a
V1 acceptance outcome.

**V2 — Mobile Client**:
After V1 Web Release, run a dedicated mobile planning iteration to produce the
mobile specification, requirements, and implementation boundary. All mobile
Development work — including native architecture, build/release, mobile auth,
offline, push, background work, and mobile client implementation — targets V2.
The V2 plan may reuse shared API contracts, but it must not expand V1 by
assumption.

**Paired Design Work**:
Design work may be created as shared, `[WEB]`, and `[MOBILE]` slices under one
product context. The mobile slice is useful evidence and may be completed in
parallel with the web slice, but it is non-blocking for the V1 web handoff and
may be deferred until V2 planning. Design pairing does not authorize mobile
Development work.

## Product language

**Recipe**:
A saved, user-usable cooking record containing instructions, ingredients, organization metadata, media, and optional import history.
_Avoid_: Recipe item, content item

**Imported Recipe**:
A Recipe created from one or more external or user-supplied sources and retaining reviewable import information.
_Avoid_: Parsed recipe, scraped recipe

**Recipe Resource**:
A piece of source or media material associated with a Recipe, including its relationship to other resources and its lifecycle state.
_Avoid_: Attachment, raw source

**Import Job**:
A durable record of one attempt to create a Recipe from submitted evidence.
_Avoid_: Import task, upload job

**Review Flag**:
A user-visible concern requiring acknowledgement or review without implying that the Recipe is unusable.
_Avoid_: Warning when referring to the domain concept

**Collection**:
A user-managed grouping of Recipes.
_Avoid_: Folder, playlist

## Planning language

**Design Domain**:
A bounded product area whose behavior, states, responsive rules, and evidence can be reviewed as one coherent design concern.
_Avoid_: Page when the concern spans multiple screens or platforms

**Core Design Baseline**:
The approved V1 product-design contract for primary web journeys, shared
product meaning, and any paired mobile evidence that is available. It is the
gate for V1 web UI implementation. V2 mobile UI has its own post-V1 planning
and design gate.
_Avoid_: Final design, mockup set

**Operational Surfaces Addendum**:
The approved design contract for admin, debug, and operational surfaces. It may complete after Core implementation starts but is required for the public release.
_Avoid_: Admin leftovers

**Design Evidence**:
Tracked research, wireframes, prototypes, screenshots, reviews, and decision records that support an approved design contract.
_Avoid_: Production source, implementation template

**Future Capability**:
A product or technical possibility retained for refinement outside the active
V1 release scope. V2 mobile work is tracked by its version label and planning
documents rather than being silently treated as V1 work.
_Avoid_: Active task, backlog ticket

**Design Track**:
The work that establishes the Core Design Baseline and Operational Surfaces Addendum.
_Avoid_: Frontend implementation

**Development Track**:
The work that builds, productionizes, operates, and verifies the product:
web implementation for V1 and mobile implementation for V2 after the
applicable design and planning gates.
_Avoid_: Production track, delivery track
