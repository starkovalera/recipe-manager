# Recipe Detail Pattern Research

Status: Proposed for user approval  
Research date: 2026-07-22  
Scope: Recipe Detail UX structure only

## Research task and boundary

This report studies current product-interface patterns that can inform the approved Recipe Detail structure without copying another product or the current Recipe Manager frontend.

The fixed Recipe Detail decisions remain fixed:

- Default Recipe View is a reading and usage context with a compact header.
- Desktop content uses a fixed-width Ingredients column and a wider Instructions column.
- Tags and Collections occupy the upper-right metadata area and collapse to a fixed visible length with `+N`.
- Import Info is a separate context available neutrally for every imported recipe.
- Cooking Focus is a simplified context; optional media uses a desktop drawer and mobile bottom sheet.
- Editing, organization, cover selection, import review, and cooking remain separate tasks.

Research may inform the two approved comparisons but does not resolve them without user approval:

1. entry behavior when unresolved import flags exist;
2. placement of difficulty and personal rating.

No production UI was used as a visual reference. No wireframe or prototype was created.

## Method

References are grouped by the Recipe Manager pattern question they help answer. First-party product documentation is used for current interaction evidence; current design-system guidance is used only where a product document does not fully describe overflow, drawer, or sheet behavior.

Each reference records:

- exact product and screen;
- current source;
- concrete interaction or layout pattern;
- fit for Recipe Manager;
- non-fit or risk;
- principle to reuse;
- elements that must not be copied.

## 1. Compact object-detail headers

### Reference 1 — Linear issue detail

**Exact product and screen**  
Linear, full issue detail view: issue title and description in the main area, with issue properties such as assignee and relations in the properties sidebar.

**Current sources**

- [Linear — Edit issues](https://linear.app/docs/editing-issues)
- [Linear — Assign and delegate issues](https://linear.app/docs/assigning-issues)
- [Linear — Issue relations](https://linear.app/docs/issue-relations)

**Concrete pattern**  
The issue title and description are directly editable in the primary content area. Secondary state and relationship properties live in a dedicated properties sidebar; the assignee is changed from that sidebar, and blocking or related objects are represented there. The main object identity remains visible while mutable metadata is spatially separated.

**Why it fits Recipe Manager**  
It demonstrates a productivity object-detail hierarchy in which the title and primary content remain dominant while compact properties stay nearby and actionable. This supports a strong recipe title, compact primary metadata, and a separate upper-right organization area.

**Why it may not fit**  
Issue properties are operational workflow controls, frequently changed by keyboard-heavy users. Recipe metadata is often read rather than changed, and the recipe cover has no equivalent in Linear.

**Principle to reuse**  
Keep object identity and task-critical content visually dominant; move secondary classification and management properties into a compact, consistently located region.

**Must not be copied**

- issue-tracker density or urgency cues;
- a permanent editable property form in Default View;
- keyboard-shortcut-first interaction assumptions;
- Linear's status, priority, or label visual language.

### Reference 2 — Notion database-page layout

**Exact product and screen**  
Notion, a database item opened as a full database page using the current Layouts system: Heading with pinned properties, main page area, and collapsible right-side details panel.

**Current source**

- [Notion — Layouts](https://www.notion.com/help/layouts)

**Concrete pattern**  
Notion separates a page into a Heading, a main content area, and an openable details panel. Selected properties can be pinned near the heading; other properties can be grouped, hidden, or moved to the details panel. The main area is reserved for information-heavy content, while the details panel can be opened and closed.

**Why it fits Recipe Manager**  
It shows how a compact object header can expose only the most useful properties while keeping a much larger metadata model available without letting it dominate the content. It also supports the distinction between primary recipe metadata and organization metadata.

**Why it may not fit**  
Notion permits up to 15 pinned properties and may put excess pinned properties into a horizontal scroller. That flexibility can produce a property-heavy header and does not guarantee a stable Recipe Detail hierarchy.

**Principle to reuse**  
Assign a strict information budget to the header: pin only information needed for immediate recognition and use, and disclose the rest in a secondary region.

**Must not be copied**

- a generic property-list appearance;
- horizontal scrolling metadata in the recipe header;
- user-configurable page-layout complexity;
- icon-and-label treatment for every field.

### Header synthesis

The strongest common principle is not “put all metadata near the title.” It is “give the header a fixed information budget.” Recipe identity, source/author inline context, time, servings, and primary actions should survive long titles and missing covers. Organization metadata must remain secondary and bounded.

For the approved difficulty/rating comparison, the references favor treating classification-like properties as secondary details unless they are demonstrably needed for the immediate task.

## 2. Productivity-oriented two-column reading layouts

### Reference 3 — Notion Simple database-page layout

**Exact product and screen**  
Notion, database page using the `Simple` layout structure with a main page and right-side details panel.

**Current source**

- [Notion — Layouts, Main page and Details panel](https://www.notion.com/help/layouts)

**Concrete pattern**  
The larger main page holds text-heavy or information-heavy modules. A narrower secondary details panel holds properties and can be opened or closed. The two regions have different semantic roles rather than being equal cards.

**Why it fits Recipe Manager**  
It reinforces asymmetric columns: a wider region for sequential content and a narrower region for scannable reference information. This is compatible with wider Instructions and fixed-width Ingredients.

**Why it may not fit**  
Notion's secondary column is a details panel, not another primary reading stream. Ingredients and Instructions are both core recipe content and must both remain visible on desktop.

**Principle to reuse**  
Give columns distinct jobs and widths based on reading behavior. The narrow column supports scanning; the wide column supports sustained sequential reading.

**Must not be copied**

- a collapsible Ingredients column on desktop;
- equal visual weight for metadata and recipe content;
- Notion module chrome;
- generic block-editor styling.

### Reference 4 — Airtable full-screen Record Detail

**Exact product and screen**  
Airtable Interfaces, full-screen Record Detail layout with a title, field groups, columns within groups, optional tab navigation, and collapsible groups.

**Current source**

- [Airtable — Interface layout: Record detail](https://support.airtable.com/docs/airtable-interface-layout-record-detail)

**Concrete pattern**  
Airtable differentiates sidesheet and full-screen detail based on task depth. Full-screen is recommended when users focus on one record, spend more time with it, or need many fields. Detail-rich pages can use grouped fields, tab navigation, collapsible groups, and multiple columns within a group.

**Why it fits Recipe Manager**  
Recipe reading is a deep single-object task. Airtable validates choosing a full page rather than a temporary panel when content is long, and it shows that grouping and columns should reflect semantic sections rather than repeated decorative cards.

**Why it may not fit**  
Airtable is field- and record-centric. A recipe is narrative and procedural; overusing collapsible groups or tabs would fragment ingredients and instructions.

**Principle to reuse**  
Use full-page space for deep single-object work, and align related sections into stable structural regions. Collapse only secondary material, never the core reading sequence by default.

**Must not be copied**

- form-field rows for read-only recipe content;
- tabs for Ingredients versus Instructions on desktop;
- charts, highlighted number modules, or database configuration controls;
- collapsible core sections merely to reduce page length.

### Two-column synthesis

The approved asymmetric Recipe Detail columns are supported by the evidence. The narrow Ingredients column should optimize repeated short-line scanning; the wider Instructions column should preserve readable line length for multi-paragraph steps. Shared top alignment and restrained separators should create one reading workspace, not two unrelated cards.

At narrower breakpoints, preserving desktop columns at unusable widths would violate the underlying principle. Mobile must switch task presentation intentionally rather than compress both columns.

## 3. Long structured content

### Reference 5 — GitHub pull request, Files changed

**Exact product and screen**  
GitHub pull request, `Files changed` tab with a navigable file tree, file filters, and the ability to hide files already viewed.

**Current source**

- [GitHub Docs — Filtering files in a pull request](https://docs.github.com/en/enterprise-cloud@latest/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/filtering-files-in-a-pull-request)

**Concrete pattern**  
GitHub keeps a long sequential review surface manageable through a compact structural index, filters, visible progress state, and temporary hiding of completed material. The file tree disappears when the viewport is too narrow or the structure is unnecessary.

**Why it fits Recipe Manager**  
The pattern demonstrates how 40 steps or 50 ingredients can remain one continuous object while gaining navigational anchors and progress cues. It also demonstrates responsive removal of a supporting navigation region when width is insufficient.

**Why it may not fit**  
Code review is comparison work, not ordinary reading or cooking. Filtering out recipe content could hide required information, and “viewed” is not equivalent to “completed while cooking.”

**Principle to reuse**  
For long structured content, preserve a stable sequence and provide orientation through section labels, numbering, and current position. Supporting navigation must adapt or disappear before it crowds the primary content.

**Must not be copied**

- diff containers and per-line controls;
- permanent progress tracking in Default View;
- file-tree visual density;
- hiding recipe content through arbitrary filters.

### Reference 6 — Apple Books reading screen

**Exact product and screen**  
Apple Books on iPhone, open-book reading screen with on-demand controls, saved reading position, return-to-previous-location control, Contents navigation, and optional Line Guide.

**Current source**

- [Apple Support — Read books in the Books app on iPhone](https://support.apple.com/en-nz/guide/iphone/iphc1af7c57/ios)

**Concrete pattern**  
The content occupies the reading surface while controls appear on demand. Closing saves the reader's place. Contents provides structural navigation, and a dedicated control returns to a previous reading location. Line Guide can focus attention on a small part of long text without changing the underlying content.

**Why it fits Recipe Manager**  
It supports preserving location, minimizing non-task chrome, and giving users an explicit way back after temporary navigation. These behaviors matter for long instructions and Cooking Focus.

**Why it may not fit**  
Books are read linearly and often hands-free; recipes require switching between ingredients and steps, scaling, checking, and handling a device in a kitchen. Pagination can obscure cross-reference between recipe sections.

**Principle to reuse**  
Treat reading position as state. Temporary controls and secondary views must return users to the exact content location they left.

**Must not be copied**

- page-turning or book-page simulation;
- typography/theme customization in the first Cooking Focus version;
- dimming all non-current content as the default;
- consumer-book visual styling.

### Long-content synthesis

Long recipes need orientation, not fragmentation. Stable step numbers, ingredient group labels where supported, predictable section starts, readable line length, and preserved scroll position are stronger than card repetition, pagination, or aggressive collapsing. Temporary cooking completion states belong in Cooking Focus, not Default View.

## 4. Collapsed Tags and Collections with `+N`

### Reference 7 — Microsoft Fluent 2 React Tag

**Exact product and screen**  
Microsoft Fluent 2 Design System, React Tag usage page, `Reflow and overflow` example.

**Current source**

- [Fluent 2 — React Tag usage](https://fluent2.microsoft.design/components/web/react/core/tag/usage)

**Concrete pattern**  
Tags may wrap by default, or a same-size interaction tag may use `+n` to represent hidden tags. Fluent requires the overflow tag to be interactive so users can access the concealed information. It also advises against truncating individual tag text.

**Why it fits Recipe Manager**  
This is a direct match for the approved fixed visible length and `+N` behavior. It preserves exact item names and gives the count a clear disclosure purpose.

**Why it may not fit**  
Fluent tags typically represent editable selections, recipients, or Planner categories. In Default View, Recipe Manager Tags and Collections are primarily read-only organization metadata.

**Principle to reuse**  
Show a stable number of complete item names and use an interactive `+N` token as an explicit disclosure control for the remaining set.

**Must not be copied**

- Fluent styling, colors, or radii;
- dismiss controls in Default View;
- truncation inside individual tag names;
- wrapping until the header grows unpredictably.

### Reference 8 — IBM Carbon operational tags

**Exact product and screen**  
IBM Carbon Design System, Tag component usage page, `Operational tag` and overflow guidance.

**Current source**

- [Carbon — Tag usage](https://carbondesignsystem.com/components/tag/usage/)

**Concrete pattern**  
Carbon distinguishes read-only, dismissible, selectable, and operational tags. Operational tags disclose related or overflow tags in another view such as a popover, modal, or detail view. Carbon warns against giving one tag multiple functions or using tags as links to unrelated pages.

**Why it fits Recipe Manager**  
It clarifies that visible Tags and Collections should be read-only in Default View while `+N` has one disclosure action. Editing remains in Organize Recipe.

**Why it may not fit**  
Carbon's pill-like tags can create the exact chip-heavy visual noise the project wants to avoid, particularly with two metadata categories near the title.

**Principle to reuse**  
Interaction semantics must be visible and singular: item tokens identify; the overflow token discloses; organization editing happens elsewhere.

**Must not be copied**

- a pill for every metadata value by default;
- colored categorical tag styling as the primary header texture;
- mixed read, edit, filter, and navigation behavior on the same token;
- a modal when a smaller popover or dedicated Organize context is more appropriate.

### Tags and Collections synthesis

Use two explicitly labeled metadata rows in the upper-right area. Each row gets a fixed item budget and one interactive `+N` control. The visible item names stay complete. On desktop, `+N` can disclose a compact, scroll-limited popover when the goal is inspection; on mobile, the same control can use a sheet. Editing must route to Organize Recipe rather than turning Default View tokens into controls.

The low-fidelity phase must test the approved dense scenario of 50 Tags and 20 Collections, including long names and keyboard access to `+N`.

## 5. Provenance and import-information workspaces

### Reference 9 — Microsoft Power Query Editor

**Exact product and screen**  
Microsoft Power Query Editor in Power BI, Excel, and Power Query Online: Queries pane, central data preview, Query Settings pane, and Applied Steps list.

**Current sources**

- [Microsoft Learn — The Power Query editor user experience](https://learn.microsoft.com/en-us/power-query/power-query-ui)
- [Microsoft Learn — Using the Applied Steps list](https://learn.microsoft.com/en-us/power-query/applied-steps)

**Concrete pattern**  
The editor separates available queries, the current result preview, and a chronological list of transformations. Selecting a step updates the central preview to show the result at that point. Step details, settings, descriptions, reordering, and deletion are available without replacing the result surface.

**Why it fits Recipe Manager**  
This is a strong analogue for comparing an extracted recipe result with source materials and extraction history. It supports the approved Import Info split view and the need to explain what was used, ignored, transformed, or flagged.

**Why it may not fit**  
Power Query is an expert transformation tool. Recipe Import Info is primarily inspection and correction, not a programmable pipeline editor. Most users should not manipulate extraction steps.

**Principle to reuse**  
Keep the interpreted result visible while users inspect the evidence or transformation that produced it. Selection in the evidence region should update or highlight the corresponding context without losing the overall result.

**Must not be copied**

- ribbon complexity;
- query language or transformation-step editing;
- expert-only terminology;
- destructive step operations as ordinary user controls;
- dense spreadsheet styling.

### Reference 10 — Airtable Record Detail revision history

**Exact product and screen**  
Airtable Interfaces, Record Detail with optional Revision history and grouped fields.

**Current source**

- [Airtable — Interface layout: Record detail](https://support.airtable.com/docs/airtable-interface-layout-record-detail)

**Concrete pattern**  
Revision history is a secondary capability attached to the current record. It can include changes from interface edits, automations, extensions, and external applications. The main record remains the anchor while provenance is available in a dedicated region.

**Why it fits Recipe Manager**  
It supports keeping import provenance attached to the recipe object but outside its ordinary reading surface. It also demonstrates that automated and external changes can be presented as understandable history.

**Why it may not fit**  
A field-change timeline is not sufficient for parent-child source relationships, used/ignored/deleted source states, or visual media evidence.

**Principle to reuse**  
Provenance should stay object-specific, chronological where meaningful, and visually subordinate to the result being explained.

**Must not be copied**

- a generic audit-log-only solution;
- database field names as user-facing language;
- one undifferentiated timeline for sources, flags, and lifecycle controls;
- exposing external-system identifiers to ordinary users.

### Reference 11 — GitHub pull request review contexts

**Exact product and screen**  
GitHub pull request with `Conversation`, `Files changed`, and `Checks` contexts; detailed check output and annotations are separate from the central discussion and change summary.

**Current sources**

- [GitHub Docs — About pull requests](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests)
- [GitHub Docs — Status checks](https://docs.github.com/en/pull-requests/reference/status-checks)

**Concrete pattern**  
One object has several task-specific inspection contexts. Overall status is visible at the object level, while detailed validation output lives in Checks and detailed evidence lives in Files changed. A failed check can block an action without permanently placing all technical detail in the primary context.

**Why it fits Recipe Manager**  
It validates a neutral `Import info` entry point and a separate detailed context containing flags, sources, and technical information. It also provides a useful comparison for keeping a concise actionable status in Default View without moving all detail there.

**Why it may not fit**  
Pull requests are collaborative approval objects. Recipes are saved content that may remain usable even with imperfect extraction evidence, and most users do not need a developer-style checks taxonomy.

**Principle to reuse**  
Surface the minimum status needed to make the primary object understandable; move evidence, diagnostics, and resolution controls into a dedicated context.

**Must not be copied**

- tab names or code-review vocabulary;
- red/green CI status as the recipe's dominant identity;
- long automated logs;
- a requirement that every import warning blocks recipe use.

### Import Info synthesis

The approved split view is supported by Power Query's result-plus-evidence model. The extracted recipe should remain visible while the evidence side is organized by user meaning: review needed, sources used, sources ignored, deleted/restorable materials, and eligible technical detail. Raw IDs and debug data require role-based progressive disclosure.

Source selection should reveal the relevant text or image and its relationship to the extracted result. It should not turn Import Info into a pipeline editor.

## 6. Focused reading or execution modes

### Reference 12 — Apple Books focused reading

**Exact product and screen**  
Apple Books on iPhone, open-book reading screen with controls hidden until the page is tapped, automatic place saving, Contents navigation, and Line Guide.

**Current source**

- [Apple Support — Read books in the Books app on iPhone](https://support.apple.com/en-nz/guide/iphone/iphc1af7c57/ios)

**Concrete pattern**  
The focused surface removes library organization and discovery chrome. Controls appear when requested. The reading position is saved automatically, and temporary navigation includes a route back to the previous location.

**Why it fits Recipe Manager**  
Cooking Focus likewise needs to remove organization, provenance, and administrative information while preserving the user's working position and temporary state.

**Why it may not fit**  
Cooking is active execution. Persistent access to portion scaling, ingredient checks, step completion, and Ingredients/Instructions switching matters more than the nearly chrome-free book experience.

**Principle to reuse**  
Focus mode should remove unrelated product contexts, not remove task controls. State and exact position survive temporary detours.

**Must not be copied**

- a fully hidden control model for core cooking actions;
- page-turn gestures;
- book typography controls;
- an immersive aesthetic that reduces practical scanning.

### Reference 13 — Linear Triage

**Exact product and screen**  
Linear, team Triage inbox and an issue opened from Triage with accept, duplicate, decline, and snooze actions.

**Current source**

- [Linear — Triage](https://linear.app/docs/triage)

**Concrete pattern**  
Items requiring intake review live outside normal workflow views by default. Opening the item in Triage places review actions in the current context, and accepting moves it into the team's normal workflow.

**Why it fits Recipe Manager**  
It is evidence for opening Import Info first when unresolved flags mean the imported result has not yet crossed a trust boundary. The dedicated context makes the pending review task explicit.

**Why it may not fit**  
A saved recipe is not necessarily unusable because one image was ignored or one quantity is uncertain. Treating every flag as a triage gate could interrupt reading unnecessarily.

**Principle to reuse**  
Route users directly into review only when unresolved state changes the object's readiness or trustworthiness; otherwise keep review available without replacing the primary task.

**Must not be copied**

- queue or inbox framing;
- accept/decline workflow terminology;
- exclusion of flagged recipes from the library;
- an assumption that all flags are equally blocking.

### Focus synthesis

Cooking Focus should preserve persistent task controls while hiding unrelated product chrome. Import review is also a focus context, but it serves trust and correction rather than cooking. These two modes must remain structurally and verbally distinct.

## 7. Desktop drawers

### Reference 14 — Airtable Record Detail sidesheet

**Exact product and screen**  
Airtable Interfaces, Record Detail opened as a resizable sidesheet over the originating list.

**Current source**

- [Airtable — Record Detail appearance: Sidesheet or full-screen](https://support.airtable.com/docs/airtable-interface-layout-record-detail)

**Concrete pattern**  
The sidesheet keeps the original list visible, can be resized per user and page, and includes next/previous controls for browsing records. Airtable recommends it when users need the originating context or continue interacting with the underlying list.

**Why it fits Recipe Manager**  
It demonstrates a non-navigation drawer that preserves the user's current context and can make room for variable content. This is relevant to optional cooking media.

**Why it may not fit**  
Airtable overlays part of the originating page, and record-to-record navigation is irrelevant. A cooking media drawer must not cover the instructions users are actively following.

**Principle to reuse**  
Use a drawer only for supplementary content that benefits from simultaneous reference to the main task. Its width and dismissal must preserve the task surface.

**Must not be copied**

- next/previous record navigation;
- a field-heavy detail sheet;
- browser-specific persistent sizing as a first-version requirement;
- overlaying the active instruction text.

### Reference 15 — IBM Carbon slide-in side panel

**Exact product and screen**  
IBM Carbon product-layout guidance, slide-in side panel acting as a grid influencer.

**Current source**

- [Carbon — 2x Grid usage, Slide-in side panels](https://carbondesignsystem.com/elements/2x-grid/usage/)

**Concrete pattern**  
The side panel is used when users need to reference the page while working with panel information. Rather than simply covering the page, the panel can resize the underlying grid and reduce its available columns.

**Why it fits Recipe Manager**  
This directly supports keeping Ingredients and Instructions visible when media opens. A responsive grid adjustment is safer than placing media on top of active steps.

**Why it may not fit**  
At tablet widths, shrinking both recipe columns plus a media panel may make all three unusable. Carbon's enterprise panel proportions are not recipe-specific.

**Principle to reuse**  
Opening supplementary media should trigger an intentional layout state, not accidental overlap. Preserve readable widths or change presentation mode at the breakpoint where that is impossible.

**Must not be copied**

- IBM grid measurements or styling;
- a panel wide enough to reduce instructions below readable width;
- enterprise form controls;
- a drawer that resets scroll or cooking checks when mounted or dismissed.

### Desktop-drawer synthesis

The recommended starting behavior is a right-side, nonmodal media drawer that intentionally reallocates width rather than covering active instructions. It needs an explicit close control, predictable focus order, and state preservation. The 1024 × 768 evaluation will determine whether both recipe columns can remain usable or whether the media presentation needs a breakpoint-specific alternative.

## 8. Mobile bottom sheets

### Reference 16 — Apple Notes nonmodal formatting sheet

**Exact product and screen**  
Apple Notes on iPhone and iPad, formatting sheet shown while text remains selectable in the parent note.

**Current source**

- [Apple Human Interface Guidelines — Sheets](https://developer.apple.com/design/human-interface-guidelines/sheets)

**Concrete pattern**  
On iOS and iPadOS, a sheet may be nonmodal when users need the sheet to affect or reference the parent view. Resizable sheets can rest at medium and large detents, expose a grabber, and expand by dragging or scrolling. Sheets use explicit Close, Done, or Back semantics according to the task.

**Why it fits Recipe Manager**  
Cooking media is supplementary to the recipe and benefits from a partial-height state that retains context, followed by full expansion for image inspection. Clear dismissal should return to the same recipe position.

**Why it may not fit**  
This is native Apple guidance, not a web implementation contract. A web sheet must work with keyboard, browser zoom, screen readers, and non-touch input rather than relying on gestures.

**Principle to reuse**  
Use a small number of meaningful sheet states. Make expansion and dismissal explicit, and preserve the parent task state independently of the sheet.

**Must not be copied**

- Apple visual materials, corner radii, or native toolbar styling;
- gesture-only controls;
- platform-specific button placement without web validation;
- a sheet for general navigation.

### Reference 17 — Material 3 modal bottom sheet

**Exact product and screen**  
Android Material 3 / Jetpack Compose, modal bottom-sheet example with explicit `SheetState`, show, hide, and dismissal behavior.

**Current source**

- [Android Developers — Bottom sheets](https://developer.android.com/develop/ui/compose/components/bottom-sheets)

**Concrete pattern**  
The sheet is modeled as explicit state rather than incidental animation. It has show, hide, visible, and dismiss transitions, and its lifecycle is separate from the parent screen content.

**Why it fits Recipe Manager**  
It reinforces that the media sheet needs a defined state model and should not own ingredient checks, completed steps, or recipe scroll position. Those states belong to Cooking Focus and survive sheet changes.

**Why it may not fit**  
The source describes an Android component implementation. A web prototype cannot assume Android gestures, back behavior, focus management, or component styling.

**Principle to reuse**  
Model media-sheet visibility and expansion explicitly, while keeping cooking progress and reading position in the parent context.

**Must not be copied**

- Material visual styling;
- Android-only lifecycle or back-button assumptions;
- a floating action button as the media entry point;
- removal of parent state when the sheet closes.

### Mobile-sheet synthesis

The first prototype should test a compact initial sheet state for thumbnails and source labels, an expanded state for preview, and a clear close action. The parent Cooking Focus retains scroll position, ingredient checks, completed steps, and the active Ingredients/Instructions context. Dragging may supplement but never replace accessible controls.

## Cross-pattern recommendations

### R1. Compact header

Keep a fixed information budget. The title, compact cover, inline source/author/time/servings, and primary actions take precedence. Tags, Collections, difficulty, rating, and other organization metadata must fit the upper-right budget or disclose elsewhere.

### R2. Two-column reading structure

Preserve asymmetric semantic columns rather than equal cards. Ingredients optimize scanning; Instructions optimize sustained reading. Use alignment, headings, and restrained rules rather than repeated containers.

### R3. Long content

Use stable numbering, meaningful group headings, readable line length, and stateful return to position. Do not paginate or arbitrarily hide core recipe content. Cooking-only completion states remain in Cooking Focus.

### R4. Tags and Collections

Show complete names for a fixed number of items and one keyboard-accessible `+N` disclosure control per row. Visible items are read-only in Default View. Inspection and editing are separate actions.

### R5. Import Info

Keep the extracted result visible beside structured evidence. Organize evidence by user meaning and source lifecycle, not internal IDs. Selecting evidence may highlight related result content; it must not expose a programmable extraction pipeline.

### R6. Cooking Focus

Remove unrelated contexts while keeping persistent cooking controls. Treat exact scroll position and temporary checks as parent state that survives media opening, closing, and expansion.

### R7. Desktop media drawer

Prefer a nonmodal right-side drawer that reallocates grid width and preserves instruction visibility. Validate the 1024 × 768 breakpoint before approving the behavior.

### R8. Mobile media sheet

Use explicit collapsed, expanded, and closed states; visible close and expansion controls; correct focus behavior; and no ownership of cooking progress state.

## Recommendations for the two unresolved decisions

### U1. Entry behavior when unresolved review flags exist

The evidence supports both approved variants under different trust assumptions:

- **Open Import Info first:** Linear Triage keeps objects requiring intake review outside the normal workflow until reviewed. This is appropriate when an unresolved flag means the extracted recipe is not yet trustworthy enough for ordinary use.
- **Open Default View with concise status:** GitHub keeps the primary pull-request context available while detailed checks and evidence live in separate contexts. This is appropriate when flags are advisory and the recipe remains usable.

**Research recommendation:** retain **Open Import Info first** as the starting hypothesis for the first low-fidelity comparison, as already approved, but evaluate it against the Default View status variant using the same flagged recipe. The comparison must test whether users understand why they landed in Import Info and can deliberately continue to Default View. Research alone cannot determine whether every current flag is severe enough to justify redirection.

The low-fidelity comparison should judge:

- clarity of why the destination changed;
- visibility of unresolved work;
- ease of continuing to the recipe;
- absence of warning treatment when no flags exist;
- neutrality of the persistent `Import info` action;
- mobile back and return behavior.

### U2. Difficulty and personal-rating placement

Linear and Notion both separate classification-like or mutable properties from the strongest object identity. Their evidence favors keeping secondary metadata together rather than expanding the primary title-and-use region.

**Research recommendation:** use **Alternative B — one compact row below Tags and Collections in the upper-right metadata area** as the starting hypothesis. It keeps organization metadata coherent and protects the title, inline source/time/servings row, and actions. Alternative A remains necessary for comparison because difficulty may prove useful at the moment someone decides whether to cook.

The paired header artifact must keep every other variable identical and test:

- discoverability without labels becoming dominant;
- relationship to Tags and Collections;
- long title and no-cover behavior;
- dense metadata behavior;
- whether difficulty feels use-critical while rating feels organizational;
- mobile reading order.

## Implications for required stress scenarios

- **S1 normal imported recipe:** ordinary Default View; neutral `Import info`; bounded metadata.
- **S2 unresolved flags:** compare the two entry behaviors without changing the neutral action.
- **S3 long title/no cover:** title and actions survive; organization metadata yields space first.
- **S4 50 Tags/20 Collections:** fixed complete names plus `+N`; disclosure is accessible and header height remains stable.
- **S5/S6 long ingredients and instructions:** stable sequence, group labels, readable widths, no card repetition.
- **S9 multiple sources/media:** Import Info result-plus-evidence split; meaningful lifecycle groups; role-gated technical detail.
- **S11 mobile cooking:** parent cooking state survives sheet interaction and exact position is restored.
- **S12 errors/loading:** error state stays in the context where it can be acted on; technical detail does not leak into Default View.

## Research critique

### Strengths

- Every requested lane has at least one current, first-party reference.
- The set spans real products and current pattern guidance rather than recipe-site aesthetics.
- References are used for interaction principles, not as visual templates.
- The research produces testable implications for dense, flagged, long-content, desktop, and mobile states.

### Limitations and risks

- Productivity and enterprise references can bias the result toward excessive density and control chrome.
- Power Query is substantially more technical than Recipe Import Info and must be simplified aggressively.
- Apple and Android sheet guidance describes native platforms; web accessibility and keyboard behavior still require prototype testing.
- Product documentation can lag small visual changes even when the documented interaction remains current.
- `+N` guidance establishes disclosure behavior but does not determine the correct visible count for Recipe Manager; that must be tested with actual header widths and long names.
- Research does not establish whether all review flags have equal severity, so it cannot settle U1 without the approved comparison.

## Elements explicitly rejected as templates

- current Recipe Manager frontend composition or styling;
- recipe-blog heroes and decorative culinary styling;
- Linear issue-tracker visual language;
- Notion generic property lists and block-editor chrome;
- Airtable database field forms;
- GitHub diff and CI styling;
- Power Query ribbon and pipeline-editing complexity;
- Fluent, Carbon, Apple, or Material component styling;
- pill treatment for every metadata value;
- card containers around every recipe section.

## Next artifact after approval

Do not create it yet.

The approved next artifact remains a behavior-first low-fidelity comparison for U1:

```text
design/recipe-detail/wireframes/01-flagged-entry-behavior-comparison.*
```

It should compare the no-flags control, Import Info-first behavior, and Default View-with-status behavior using the same realistic imported recipe. U2 should follow in a separate paired header artifact.

## Approval requested

Approve or revise:

1. the reusable principles for all eight research lanes;
2. the Import Info-first starting recommendation for U1;
3. the upper-right placement starting recommendation for U2;
4. the stated implications for dense, long-content, flagged, desktop, and mobile states.

No wireframe or prototype work should begin until this report is approved.
