# pen.dev for the Recipe Manager design workflow

Status: research recommendation, not a tool adoption decision
Researched: 2026-08-19

## Question

Can [pen.dev](https://www.pen.dev/) make Recipe Manager's design work easier for
a person to understand: what is approved, unfinished, or blocked; which screens
and states exist; how journeys move between them; and where the authoritative
decision, issue, prototype, screenshot, and implementation evidence lives?

## Executive conclusion

**Yes, as a repo-local visual projection; no, as the design workflow's source of
truth.**

Pen is a strong candidate for a panoramic, human-readable atlas because its
infinite canvas has screen-sized frames, reusable components, notes, hyperlinks,
and arbitrary entity metadata. Its JSON-based `.pen` file can live in the
repository and be reviewed with the same Git history as the design artifacts.
Pen also supports Codex through a local MCP server and has a headless CLI for
rendering or batch edits. These are unusually good matches for Recipe Manager's
repository-first design practice.

The important limitation is that Pen does **not** currently document first-class
GitHub issue synchronization, approval states, review threads, or interactive
screen-to-screen prototype transitions. A Pen canvas can show status badges and
draw journey arrows, but those would be representations created by us. The
official `.pen` schema documents graphical objects, notes, links, context, and
metadata, but no interaction or transition model. A browser share is a frozen
snapshot, not a live status dashboard.

The recommended next step is therefore a narrow pilot: create one derived Pen
atlas for the mature Recipe Detail/Edit domain, link every item back to current
repository/GitHub evidence, and keep the existing interactive HTML prototypes.
Do not migrate decisions, approvals, issue status, or prototypes into Pen.

## Current Recipe Manager problem

The repository already contains the right kinds of evidence:

- a cross-domain status and dependency roadmap in
  [`design/roadmap.md`](../../roadmap.md);
- a detailed scope and decision inventory in
  [`scope-and-decision-inventory.md`](../scope-and-decision-inventory.md);
- feature-level current decisions and an explicit supersession trail;
- numbered interactive prototypes, screenshots, reviews, and a permanent
  [Recipe Detail decision gallery](../../recipe-detail/prototypes/00-decision-gallery/README.md);
- GitHub issues as the current task and dependency tracker.

The problem is navigation and synthesis rather than missing evidence. A person
must traverse several Markdown files, issue bodies, prototype folders, and
screenshots to reconstruct one mental model.

There is also a concrete synchronization warning in the current snapshot. On
2026-08-19, [tracker #29](https://github.com/starkovalera/recipe-manager/issues/29)
was still open and its checklist still showed #21 and #22 as unfinished, while
[PR #80](https://github.com/starkovalera/recipe-manager/pull/80) and
[PR #82](https://github.com/starkovalera/recipe-manager/pull/82) were already
merged. The checked-out roadmap still described both deliveries as draft PRs.
This is exactly why a new visual surface must not introduce another manually
maintained status authority.

## What Pen verifiably provides

### Repo and agent fit

Pen describes `.pen` as a JSON-based, portable, version-control-friendly design
format. The documented workflow is to keep the file beside the code, commit it,
view text diffs, and branch or merge it with Git
([`.pen` files](https://docs.pen.dev/core-concepts/pen-files),
[Design as Code](https://docs.pen.dev/core-concepts/design-as-code)). The
developer schema exposes stable object IDs, names, `context`, `metadata`, notes,
and text hyperlinks; it also supports reusable components and themes
([`.pen` format](https://docs.pen.dev/for-developers/the-pen-format)).

Pen's MCP integration officially lists Codex and provides read/write design
operations, screenshots, layout analysis, variables, and themes. The MCP server
runs locally, although the product's application source is not public
([AI integration](https://docs.pen.dev/getting-started/ai-integration)). The CLI
can create or modify `.pen` files, export PNG/JPEG/WEBP/PDF, and run batch tasks
([CLI](https://docs.pen.dev/for-developers/pen-cli)).

These capabilities make it feasible to keep the atlas in Git, ask an agent to
reconcile it against repository context, and export a deterministic overview
image for a PR or issue.

### Visual inventory fit

Pen's infinite canvas and frames are a natural surface for:

- one card per Design Domain;
- one frame per screen/state combination;
- spatial grouping by journey, platform, feature, or lifecycle stage;
- reusable visual status badges and evidence-link components;
- solid arrows for blockers and dashed arrows for non-blocking inputs, matching
  the repository's existing dependency convention;
- visible historical/superseded lanes instead of overwriting evidence.

The official interface documentation says that frames define screen boundaries
and that reusable components have a source and instances
([interface](https://docs.pen.dev/core-concepts/pencil-interface)). The format's
`href` and `metadata` fields can link a visible card to an issue, exact decision
document, HTML prototype, or screenshot without copying the underlying contract
into the canvas.

### Human viewing

Pen exposes browser links for frozen design snapshots, with no install required
([shared-design viewer](https://app.pen.dev/)). This is useful for a review
checkpoint or a PR attachment. It is not evidence of live collaboration,
comments, or automatic refresh; the official viewer explicitly calls the shared
artifact a frozen snapshot.

### Design/code bridge

Pen documents agent-mediated code-to-design import, design-to-code generation,
and CSS-variable/token synchronization
([Design and Code](https://docs.pen.dev/design-and-code/design-to-code)). That is
potentially useful later for visual-system work, but it should not be used to
copy Recipe Manager's isolated prototype code into production or turn existing
production UI into the visual baseline. The repository's design/production
boundary remains authoritative.

## Fit against the requested goals

| Goal | Pen fit | Required Recipe Manager convention |
| --- | --- | --- |
| See what is ready, open, blocked, or superseded | Medium. Badges, colors, notes, themes, and metadata can express the states, but Pen has no documented approval/issue workflow. | Render status from GitHub and current decision records. Never treat a badge edited only in Pen as authoritative. |
| Inventory screens and difficult states | Strong. Frames, components, themes, notes, screenshots, and infinite-canvas grouping fit a screen/state atlas well. | Use stable IDs and a consistent `domain / screen / state / platform` naming scheme. Keep sparse, normal, dense, loading, error, permission, and responsive variants explicit. |
| Understand transitions and user journeys | Medium for a diagram; weak for an interactive prototype. The canvas can contain arrows and linked frames, but the documented schema has no interaction/transition object. | Draw the canonical journey as a map and link nodes to the existing interactive HTML prototypes for behavior. |
| Navigate to decisions, issues, prototypes, and screenshots | Strong. Text links and metadata can point to repository and GitHub evidence. | Every approved or blocked claim must have an evidence link. A canvas description may summarize but must not duplicate the full decision. |
| Review in Git | Strong in principle: JSON file, text diff, branches, and merges are documented. | Pilot real concurrent edits and inspect diff quality before calling merges safe. Use frequent commits because Pen has no autosave. |
| Review without installing Pen | Medium. Frozen browser snapshots and exported images work. | Publish the current snapshot/export from a known commit and label its source revision and generation time. |
| Collect feedback and approvals | Weak/unknown. No official Pen documentation was found for comments, reviewer roles, approval gates, or resolved threads. | Keep approval in the feature decision log/user gate and actionable work in GitHub. |

## The Threads report: useful anecdote, not product documentation

The supplied [Threads conversation](https://www.threads.com/share/ICOsMwNvY/)
supports the intended use case, but only anecdotally. The author said they used
Pen to think through UX, asked it to connect all screens into a user journey,
and found the resulting scheme useful. They also advised establishing the
design system before asking an agent to produce code. Those observations align
with the proposed atlas and with Recipe Manager's existing separation between
approved UX contracts and production implementation.

The same thread contains unverified claims about price/model access, a question
about Figma-like sharing, and a comment naming `OpenDesign` without a URL. None
of these comments should be treated as a Pen or OpenDesign product fact.

## Alternatives worth comparing

Only two alternatives are competitive for this specific combination of visual
flows, human review, agent use, and repository proximity.

### Penpot: strongest reviewer and clickable-flow alternative

[Penpot](https://penpot.app/) has first-class board-to-board prototype
connections, triggers, transition animations, multiple named flows, and a
shareable link for each flow
([prototyping documentation](https://help.penpot.app/user-guide/prototyping-testing/prototyping/)).
Its View mode supports public prototype links, optional comments, and inspect
permissions
([View mode](https://help.penpot.app/user-guide/prototyping-testing/testing-view-mode/)).
Its native export is an inspectable ZIP containing JSON metadata and assets
([file format](https://help.penpot.app/user-guide/export-import/penpot-file-format/)).

Penpot is therefore better than Pen when the primary outcome is a clickable
walkthrough that non-developers can comment on. It is weaker for this
repository-first workflow: the design normally lives in a Penpot workspace,
and the `.penpot` export is an archive rather than a continuously edited,
plain-JSON repo file. It also does not by itself solve GitHub issue/approval
synchronization. Choose Penpot instead only if first-class interactive flows and
review comments matter more than branch-local design-as-code.

### `OpenDesign`: competitive for executable prototypes, identity unconfirmed

The Threads comment does not include a link, so the exact product cannot be
identified from the conversation. The strongest candidate is the project that
explicitly documents `OpenDesign`, `Open Design`, `open-design`, and
`opendesign` as aliases and names
[open-design.ai](https://open-design.ai/official/) plus
[`nexu-io/open-design`](https://github.com/nexu-io/open-design) as its canonical
surfaces. This identification is plausible, **not confirmed**. Other similarly
named projects, including Open CoDesign and skill-only OpenDesign repositories,
must not be conflated with it.

The candidate OpenDesign is local-first, open source, works with Codex and other
coding agents, uses editable `DESIGN.md` systems, and generates real HTML/CSS
prototypes in a sandboxed preview. Its official repository describes web,
desktop, and mobile prototype artifacts and project-local files. This makes it
more capable than Pen for demonstrating real interaction and a custom status
dashboard.

For the current goal it is less direct: it generates executable artifacts
rather than providing a dedicated panoramic vector atlas, and its official
materials do not establish GitHub status synchronization or an approval
workflow. Adopting it for the design cockpit would effectively create and
maintain another small application. It is worth a separate pilot only if the
team decides that live, custom interactions inside the overview are mandatory.

### Comparison

| Criterion | Pen | Penpot | Candidate OpenDesign |
| --- | --- | --- | --- |
| Repo-local, text-reviewable working artifact | Strong: plain JSON `.pen` is the normal working file | Partial: inspectable JSON is inside an exported ZIP | Strong for generated HTML/CSS/project files |
| Panoramic screen/state atlas | Strong | Strong | Possible, but would be custom-built |
| First-class clickable screen transitions | Not documented | Strong | Strong through executable HTML |
| Public human review | Frozen snapshot/export | Strong share links, optional comments and inspect | Executable preview/export; collaboration/approval still separate |
| Codex/agent integration | Official local MCP and CLI | Official MCP exists, but workspace/export lifecycle is separate | Official Codex/CLI integration |
| Native issue/approval status | None documented | None documented | None documented |
| Main risk | A beautiful but stale second status board | Drift between hosted workspace/export and repo evidence | A second custom app and duplicated prototype surface |

## Recommended integration contract

### Sources of truth remain unchanged

1. **Work status and dependencies:** GitHub issues, PRs, and their native
   blocker relationships.
2. **Approved, rejected, unresolved, and superseded behavior:** the current
   feature decision document plus its decision log.
3. **Behavioral evidence:** numbered isolated HTML prototypes, tests, reviews,
   and screenshots.
4. **Cross-domain plan:** `design/roadmap.md` and shared inventory.
5. **Pen canvas:** a human-readable projection and navigation surface only.

### Model two independent status dimensions

Do not collapse approval and delivery into one color. Each screen/state card
should show both:

- **Design:** `unexplored`, `in design`, `awaiting approval`, `approved`, or
  `superseded`;
- **Delivery:** `not planned`, `blocked`, `ready`, `in progress`, `merged`, or
  `verification needed`.

Every non-neutral status needs a source link and an `as of` revision/date.
Unknown or contradictory evidence should be visible as `verification needed`,
not guessed by the agent.

### Canvas information architecture

Use three zoom levels in one cross-feature atlas:

1. **Portfolio:** Design Domains, V1/V2 boundary, blockers, and baseline gate.
2. **Journey:** entry/exit nodes and solid/dashed transitions for one user goal.
3. **Screen/state:** desktop/mobile frames, difficult states, approval/delivery
   badges, and evidence links.

Keep superseded evidence in a clearly separated history lane. Link to the
existing interactive prototype instead of recreating its behavior in Pen.

### Refresh discipline

The stable mapping between a visual node and its evidence may be configured,
but mutable status should be read from GitHub/current decision files during a
refresh. A refresh must surface contradictions rather than silently choosing
one source. The exported image and browser snapshot should include the source
commit and refresh timestamp.

Do not start by writing a custom `.pen` parser or relying on undocumented fields.
The official format documentation warns that breaking changes may occur. Use
Pen's supported MCP/CLI operations for the pilot and decide whether deterministic
generation is viable only after inspecting the resulting diffs.

## Small pilot

Pilot only the Recipe Detail/Edit domain; it already has approved foundations,
open work, responsive variants, difficult states, superseded iterations, and an
interactive gallery.

1. Create one repo-local atlas file under a new cross-feature design-operations
   location, leaving all existing decision/prototype artifacts untouched.
2. Add a portfolio strip containing Recipe Detail/Edit and the adjacent domains
   needed to understand entry and exit points.
3. Add three journeys: read a recipe, edit-and-save with validation/dirty guard,
   and inspect imported resources/manage media.
4. For each included screen/state, show the two-dimensional status, exact
   evidence links, platform, and source revision. Reuse screenshots as evidence;
   do not redraw already approved behavior merely for visual polish.
5. Export one overview image and one frozen browser snapshot, then ask a person
   unfamiliar with the file layout to answer the acceptance questions below.
6. Re-check GitHub and the decision log, refresh the atlas, and inspect the Git
   diff. This tests the most important failure mode: staleness.

### Pilot acceptance questions

A reviewer should be able to answer within two minutes:

- What is approved but not implemented?
- What is unfinished or blocked, and by what?
- Which desktop and mobile states exist for Recipe Edit?
- Which transition occurs on Save success, Save failure, and unsaved exit?
- Where is the exact decision and interactive evidence for each claim?
- Which artifacts are superseded rather than current?

The pilot succeeds only if all answers match GitHub and repository sources, the
atlas is understandable without Pen authoring knowledge, and a refresh produces
a reviewable diff. If reviewers primarily need to click through transitions and
comment, repeat the same slice in Penpot before adopting Pen. If they need a
custom live dashboard, test the candidate OpenDesign separately.

## Limitations and open questions

- No official Pen documentation was found for clickable prototype transitions,
  comments, approval gates, resolved review threads, or GitHub synchronization.
- The official `.pen` schema is documented but explicitly allowed to introduce
  breaking changes.
- Pen's application source is private; the open claim applies to the file
  format, not the editor implementation.
- Frozen browser snapshots improve accessibility but are not live views; their
  sharing controls and private-repository implications need a real pilot.
- Git merge quality is claimed but untested here, especially for simultaneous
  spatial edits to one canvas.
- Pen has no autosave. The documentation recommends frequent saves and Git
  commits.
- Pen documents a known issue where setup may modify or duplicate Codex
  `config.toml`; back up and inspect the configuration during the pilot.
- The CLI requires Pen authentication; CI use requires a Pen CLI key and model
  credentials. No secret belongs in the repository.
- The supplied Threads post is personal experience, not a reproducible product
  test.
- The exact `OpenDesign` named in the comments remains unverified because the
  commenter supplied no link.

## Recommendation

Proceed with a **time-boxed Pen pilot as a derived design atlas**. It offers the
best current balance of repo locality, visual mapping, agent operation, and
human readability. Preserve the existing gallery and prototypes as behavioral
evidence, and make evidence links plus refresh discipline non-negotiable.

Do not adopt Pen as an approval tracker, backlog, or replacement for current
decision documents. Prefer Penpot if the pilot reveals that clickable flows and
review comments are the dominant need. Evaluate the candidate OpenDesign only
for a separate executable-cockpit use case, after confirming that it is the
product the commenter meant.
