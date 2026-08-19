# Pen and Penpot for Recipe Manager design operations

Status: research recommendation, not an adoption decision
Verified: 2026-08-19

## Decision to make

Recipe Manager needs more than another drawing tool. The target system must:

1. give a person one centralized, visual, interactive representation of
   screens, features, difficult states, and transitions;
2. stay current with little manual effort by fitting Git, GitHub issues/PRs,
   the repository task lifecycle, approval gates, and post-merge ceremonies;
3. have a genuinely usable free mode, not a demo that immediately loses the
   required collaboration or automation features.

This review evaluates [Pen](https://www.pen.dev/) and
[Penpot](https://penpot.app/) against those requirements using current official
product documentation. The supplied Threads post is kept as anecdotal evidence
only. `OpenDesign` remains a secondary comparison because the comment did not
identify the product with a link.

## Bottom line

**Neither Pen nor Penpot alone satisfies all three requirements.**

- **Pen** is the stronger repository projection engine. A plain-JSON `.pen`
  file lives in Git; Codex can update it through local MCP; a headless CLI can
  batch-edit and export in CI; and Code on Canvas can render data-driven layers
  from a watched repository `.js` file. But Pen has no documented first-class
  screen-to-screen prototype interactions, comments, approval workflow, or
  GitHub synchronization. Its shared browser view is a frozen snapshot.
- **Penpot** is the stronger human interaction and review surface. It has real
  board-to-board connections, triggers, transitions, multiple flows, public
  prototype links, comments, inspect mode, and a materially useful free plan.
  But its design workspace is outside Git. Its MCP operates through an open
  Penpot file and connected plugin/current page, while its API/webhook surface
  requires a custom integration whose official webhook documentation is still
  intentionally incomplete. That is not an unattended, low-effort lifecycle
  synchronization path.

The recommendation is a **repository-owned design graph plus generated web
cockpit**, integrated into lifecycle commands and CI. Keep GitHub and decision
records authoritative; generate the human view from them. Use Pen only if a
spatial authoring canvas materially improves that generated view. Use Penpot
only for journeys where real clickable transitions and stakeholder comments
justify a separate hosted design surface.

## Why synchronization is the deciding constraint

The repository already has the right evidence:

- cross-domain plan and dependencies in [`design/roadmap.md`](../../roadmap.md);
- scope and discrepancies in
  [`scope-and-decision-inventory.md`](../scope-and-decision-inventory.md);
- feature-level approvals and supersessions;
- numbered HTML prototypes, screenshots, reviews, and the
  [Recipe Detail decision gallery](../../recipe-detail/prototypes/00-decision-gallery/README.md);
- GitHub issues and PRs as task/delivery state.

The problem is synthesis and drift. On 2026-08-19,
[tracker #29](https://github.com/starkovalera/recipe-manager/issues/29) still
showed #21 and #22 unfinished while
[PR #80](https://github.com/starkovalera/recipe-manager/pull/80) and
[PR #82](https://github.com/starkovalera/recipe-manager/pull/82) were already
merged. The checked-out roadmap still called both deliveries draft PRs.

A manually maintained visual board would add a third stale account. Any adopted
surface must therefore be a **derived projection** with a verifiable source
revision, not another authority for task or approval status.

## Pen: verified capabilities and limits

### Central visual representation

Pen is well suited to a panoramic atlas. Its infinite canvas, screen-sized
frames, reusable components, notes, themes, hyperlinks, `context`, and arbitrary
entity metadata can represent domains, screens, states, evidence, blocker
arrows, and superseded history. The official `.pen` format is JSON-based and
documents stable object IDs, text links, notes, metadata, components, and themes
([format](https://docs.pen.dev/for-developers/the-pen-format),
[interface](https://docs.pen.dev/core-concepts/pencil-interface)).

The file is intended to live beside code and be committed, diffed, branched,
and merged with Git
([`.pen` files](https://docs.pen.dev/core-concepts/pen-files),
[Design as Code](https://docs.pen.dev/core-concepts/design-as-code)). This is a
strong fit for provenance and branch-local design work.

### Code on Canvas is data-driven, not application interactivity

[Code on Canvas](https://docs.pen.dev/core-concepts/code-on-canvas) lets a Script
node reference a repository `.js` file. Pen watches the file; saving it reruns
the script and re-renders derived nested layers. Inputs exposed in the properties
panel can parameterize the output. This could render a status matrix or flow
layout from generated lifecycle data with much less manual canvas editing.

It does **not** provide a browser application runtime. Officially, scripts:

- return Pen node arrays;
- run synchronously in a sandbox;
- have no DOM, network, filesystem, timers, or async access;
- are limited to 1,000 returned nodes and two seconds;
- re-render only when their file, size, or exposed inputs change.

That makes Code on Canvas valuable for deterministic visualization, not for
clickable buttons, stateful navigation, or animated screen-to-screen prototype
transitions. The current `.pen` schema also documents no interaction/transition
object. Text hyperlinks can navigate to evidence, but that is not an interactive
product flow.

### MCP, headless CLI, and CI

Pen officially supports Codex through a local MCP server that can read and
modify the current `.pen` file
([AI integration](https://docs.pen.dev/getting-started/ai-integration)). The
[CLI](https://docs.pen.dev/for-developers/pen-cli) uses the same editor engine
headlessly and supports:

- scripted create/update operations and document inspection;
- input/output `.pen` files without a GUI;
- sequential JSON batch tasks;
- screenshot and PNG/JPEG/WEBP/PDF export;
- CI authentication with an organization-scoped `PEN_CLI_KEY` plus model
  credentials.

This is the best automation story of the two products. It is still not native
Recipe Manager synchronization: we would have to write and maintain the adapter
that reads GitHub/current decision records, resolves contradictions, generates
the data/script, invokes Pen, and checks the diff. Agent-prompted regeneration
must also be tested for deterministic output before it can become a required CI
step.

### Sharing and review

Pen's official web viewer opens a
[frozen shared snapshot](https://app.pen.dev/) without an installation. No
official documentation was found for live reviewer comments, resolved threads,
approval states, or role-based design review. A frozen snapshot is useful as PR
evidence but is not an always-current cockpit.

### Free use

Pen's current [pricing page](https://www.pen.dev/pricing) says only that Pen is
currently free and that paid features or plans may be introduced later. It
publishes no free-plan limits, quotas, collaboration entitlement, or long-term
free-tier guarantee. The editor therefore passes a present-day cost check, but
not the stronger test of a documented durable and bounded free plan. AI usage
also relies on external model/subscription or API access, and CI explicitly
requires model credentials.

## Penpot: verified capabilities and limits

### Real flows and human review

Penpot has the native interaction model that Pen lacks. It connects boards with
hotspots and connector wires; supports click, hover, leave, and delay triggers;
provides navigation, overlay, toggle, close, back, and open-URL actions plus
dissolve, slide, and push transitions; and allows multiple named flow starting
points with separate shareable links
([prototyping](https://help.penpot.app/user-guide/prototyping-testing/prototyping/)).

View mode can play those interactions, expose a board thumbnail overview, share
the prototype publicly, allow comments, and optionally allow code inspection
([View mode](https://help.penpot.app/user-guide/prototyping-testing/testing-view-mode/)).
For a non-developer reviewer asking "where can I go from this screen?", Penpot
is substantially more complete than Pen.

### MCP and automation constraints

The official [Penpot MCP server](https://help.penpot.app/mcp/) can read and edit
components, styles, tokens, pages, layers, and prototype interactions. It
supports Codex and can run remotely or locally.

Its operating model matters:

- the MCP plugin inside Penpot connects the **open design file** to the server;
- the user must open a file and connect the plugin;
- operations act on the currently focused page;
- local MCP requires a running npm server, an open browser tab, and the plugin
  window kept connected;
- remote MCP avoids the local server but can access only what Penpot exposes,
  not the repository filesystem.

This is useful interactive agent assistance, not a documented unattended
headless/CI renderer comparable to Pen's CLI.

### API and webhooks

Penpot has personal access tokens, an internal RPC-style API, and team-level
outbound webhooks for events such as file updates and comments
([integration guide](https://help.penpot.app/technical-guide/integration/)).
That makes a GitHub/DesignOps bridge possible in principle.

The same official guide is explicit about maturity: the integration system is
"relatively simple"; there is no specific webhook event documentation; backend
RPC specifications are the temporary guide; webhook payloads may omit or add
fields; and the recommended discovery method is observing real payloads. A
production-quality bidirectional sync would therefore be a custom service with
contract tests, retries, reconciliation, secret management, and maintenance.
It is not low effort.

The official `penpot-export` CLI is narrower than a design-graph synchronizer:
it exports design tokens and page component styling to CSS/SCSS/JSON, not a
complete editable screen/transition workspace
([official repository](https://github.com/penpot/penpot-export)).

### Repository fit and export

The current `.penpot` export is an inspectable ZIP containing JSON metadata and
binary assets. Export and import are documented as workspace/dashboard actions;
imports are limited to 1 GB
([export/import](https://help.penpot.app/user-guide/export-import/export-import-files/),
[file format](https://help.penpot.app/user-guide/export-import/penpot-file-format/)).

This is open and backup-friendly, but it is not the same as editing a plain
repository file on every branch. Tracking periodic ZIP exports would create
opaque Git diffs and still require a ceremony to keep the hosted workspace and
repository snapshot aligned.

### Free plan

Penpot has a materially usable documented free tier. The current
[pricing page](https://penpot.app/pricing) lists the Professional cloud plan at
$0/user/month with:

- all core design, prototype, transition, flow, sharing, comments, inspect,
  API, webhook, and AI-workflow features;
- up to 8 team members and unlimited viewers;
- unlimited design files within storage capacity;
- 10 GB storage;
- 7 days of autosaved versions and deleted-file recovery.

Penpot is also open source and can be self-hosted, though self-hosting transfers
operational cost to the project. For the present small team, the hosted free
plan is genuinely usable without removing any required interaction or review
feature.

## Weighted decision matrix

Scoring: `0` absent, `1` weak, `2` partial/high custom effort, `3` workable with
a bounded adapter, `4` strong, `5` native/complete. Weighted totals are out of
100. A tool still fails the decision if either critical requirement—real
interactive transitions or low-effort lifecycle synchronization—scores below 4,
regardless of its total.

| Criterion | Weight | Pen | Penpot | Evidence-based rationale |
| --- | ---: | ---: | ---: | --- |
| Central screen/feature/state map | 20% | 5 | 5 | Both have capable infinite canvases and reusable structure. |
| Real interactive flows and reviewer access | 20% | 1 | 5 | Pen documents static vectors/links and frozen shares; Penpot has native interactions, transitions, flows, public shares, and comments. |
| Low-effort lifecycle synchronization | 30% | 3 | 2 | Pen has repo-local JSON, watched scripts, headless CLI, batch, and CI, but needs our GitHub/decision adapter. Penpot has MCP/API/webhooks, but MCP needs an open connected file and the webhook/API bridge is custom and immature. |
| Git review, provenance, and branch fit | 15% | 5 | 2 | `.pen` is a normal text repo artifact; `.penpot` is normally a hosted workspace and exports as a ZIP. |
| Genuinely usable free mode | 15% | 3 | 5 | Pen is currently free but publishes no tier/limits guarantee and CI needs model credentials. Penpot documents a full-featured $0 plan with concrete team/storage/history limits. |
| **Weighted total** | **100%** | **66/100** | **73/100** | Neither passes both critical requirements. |

### Decision

- Choose **Pen** only if the primary experiment is a Git-native, automatically
  rendered spatial atlas and links to existing HTML prototypes are sufficient.
- Choose **Penpot** only if clickable journeys and stakeholder review are worth
  accepting a hosted design source plus a custom synchronization boundary.
- Do **not** adopt either as the sole design-operations system.

## Recommended workflow architecture

### 1. Repository-owned design graph

Add a small machine-readable graph under `design/shared/` only after a separate
implementation approval. It should contain stable identifiers and evidence
relationships, not manually copied mutable status:

- domain, journey, screen, state, and transition IDs;
- exact decision, prototype, screenshot, review, issue, and PR links;
- source selectors that tell a refresh job where approval/delivery state comes
  from;
- explicit platform and V1/V2 boundary;
- solid blocker versus dashed non-blocking dependency semantics.

GitHub and current decision documents remain authoritative. The refresh job
must render contradictions as `verification needed`, never guess.

### 2. Generated interactive web cockpit

Generate a static browser application from that graph and the existing
prototype/gallery assets. This gives one centralized surface with:

- portfolio, journey, and screen/state zoom levels;
- clickable transitions between screen states;
- independent **Design** and **Delivery** statuses;
- links or embedded launch points for the existing isolated HTML prototypes;
- approved, blocked, unresolved, superseded, and stale evidence views;
- source commit and refresh timestamp.

This is the only option reviewed here that can satisfy all three criteria at
once: real browser interactivity, deterministic repository generation, and no
tool subscription cost. It also extends the existing decision-gallery practice
instead of replacing it.

### 3. Lifecycle integration

Make synchronization a normal ceremony rather than a separate manual task:

1. **Preflight / issue start:** refresh GitHub state and validate graph links.
2. **Approval gate:** record the approval in the feature decision log; graph
   status is derived on refresh.
3. **Prototype verification:** add permanent evidence links and run cockpit
   navigation/link checks.
4. **PR publication:** generate the cockpit snapshot and fail CI on stale or
   contradictory status where a deterministic rule exists.
5. **Post-merge:** refresh merged PR/issue state, update the generated artifact,
   and reconcile roadmap wording in the same maintenance change.

The repository can store a cached GitHub snapshot for reproducible builds, but
it must carry `asOf`, source URL, and source revision. Secrets remain in CI, not
in design artifacts.

### 4. Optional tool roles

- **Pen role:** render a spatial companion from the same generated data using
  Code on Canvas; export an overview for PRs. Never edit operational status only
  in Pen.
- **Penpot role:** author and review selected complex journeys with real
  transitions/comments. Store the canonical Penpot file/flow IDs in the graph,
  and export a versioned backup at explicit release/approval checkpoints rather
  than pretending it is continuously Git-native.

Neither optional role is required for the first cockpit pilot.

## Pilot and acceptance test

Pilot the Recipe Detail/Edit domain because it contains approved structure,
unfinished work, responsive variants, difficult states, superseded iterations,
and interactive prototypes.

1. Model three journeys: read a recipe; edit/save with validation and dirty
   guard; inspect imported resources/manage media.
2. Generate one web cockpit page from repository/GitHub evidence.
3. If desired, generate the same static graph in Pen and create one Penpot flow
   for the edit/save journey; measure incremental maintenance rather than visual
   appeal.
4. Simulate a PR merge and an approval change, run the lifecycle refresh, and
   inspect the Git diff.

A reviewer unfamiliar with the repository should answer within two minutes:

- What is approved but not delivered?
- What is blocked, by what, and on which platform/release boundary?
- Which screen states and transitions exist?
- What is current versus superseded?
- Where is the exact decision and executable evidence?

The pilot succeeds only if the answers match GitHub/current decision records,
the generated diff is reviewable, and status refresh needs no manual canvas
editing. That final condition is more important than which tool produces the
prettiest overview.

## Threads and OpenDesign notes

The supplied [Threads conversation](https://www.threads.com/share/ICOsMwNvY/)
is consistent with the use case but is not product documentation. The author
reported asking Pen to connect all screens into a user journey and finding the
resulting scheme useful; they also recommended defining the design system before
agent-driven coding. This supports testing a visual atlas, not claiming that Pen
has native interactive transitions or automatic lifecycle sync.

A comment names `OpenDesign` without a URL. The likeliest current project is the
one that explicitly declares `OpenDesign`, `Open Design`, `open-design`, and
`opendesign` as aliases:
[open-design.ai](https://open-design.ai/official/) and
[`nexu-io/open-design`](https://github.com/nexu-io/open-design). The identity is
plausible, not confirmed; similarly named projects must not be conflated.
That candidate generates executable HTML/CSS prototypes and could build the web
cockpit, but it would still be a generator around the repository-owned graph,
not the source of task/approval truth.

## Remaining unknowns and risks

- Pen publishes no durable free-plan entitlement or limits; "currently free"
  can change.
- Pen documents no first-class interactive prototype model, comments, approval
  workflow, or GitHub integration.
- Pen's schema may introduce breaking changes, has no autosave, and its editor
  source is private even though the file format is open.
- Pen setup may modify or duplicate Codex `config.toml`; inspect configuration
  during any pilot.
- Penpot's API/webhook payload contract is not documented strongly enough to
  assume a maintenance-free bidirectional integration.
- Penpot MCP is oriented around a live open file/current page, not unattended
  CI.
- Penpot's hosted workspace and Git branches have different concurrency and
  provenance models; exported ZIP backups do not solve that automatically.
- Neither tool has been exercised against this repository in this research.

## Recommendation

Do not select a design SaaS as the architecture. Build the minimal
repository-owned graph and generated interactive cockpit first, integrate its
refresh into the existing lifecycle, and prove that it stays current through a
real merge.

After that proof:

- add Pen only if its spatial canvas and CI export save review time without
  introducing nondeterministic diffs;
- add Penpot only for journeys where native transitions, sharing, and comments
  produce enough review value to justify the hosted synchronization boundary.

This keeps the workflow understandable, current, and free even if either
vendor's product or pricing changes.
