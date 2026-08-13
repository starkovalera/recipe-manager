# Recipe Manager

Recipe Manager is a product for importing, organizing, reviewing, editing, finding, and using recipes across web and mobile clients.

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
The approved first-version product-design contract for primary web and mobile user journeys. It is the gate for production UI implementation.
_Avoid_: Final design, mockup set

**Operational Surfaces Addendum**:
The approved design contract for admin, debug, and operational surfaces. It may complete after Core implementation starts but is required for the public release.
_Avoid_: Admin leftovers

**Design Evidence**:
Tracked research, wireframes, prototypes, screenshots, reviews, and decision records that support an approved design contract.
_Avoid_: Production source, implementation template

**Future Capability**:
A product or technical possibility retained for refinement outside the active first-version scope.
_Avoid_: Active task, backlog ticket

**Design Track**:
The work that establishes the Core Design Baseline and Operational Surfaces Addendum.
_Avoid_: Frontend implementation

**Development Track**:
The work that builds, productionizes, operates, and verifies the product, including web and mobile implementation after the applicable design gate.
_Avoid_: Production track, delivery track
