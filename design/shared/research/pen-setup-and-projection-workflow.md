# Pen setup and Recipe Manager projection workflow

Status: Core experiment selected in #90; human setup #89 complete; #96 evidence
prepared and adoption pending<br>
Verified: 2026-08-22

## Question and conclusion boundary

This note turns the accepted repository boundary in
[`ADR-0007`](../../../docs/adr/0007-repository-owned-design-operations-cockpit.md)
into an executable setup and pilot outline. It answers how Pen could be tried on
Windows with Codex, what it would add to the repository, and what a first
projection would cost. It does **not** decide whether to adopt Pen.

On 2026-08-20, the project selected the **Core** experiment described below.
Other product Design tasks remain on a temporary planning hold until the
experiment produces an explicit continue/stop decision. The current path is:

1. keep the repository-owned graph and generated web cockpit authoritative;
2. prove a current-state-only Recipe Detail projection through local MCP;
3. measure whether `.pen` diffs and exports are stable enough;
4. only then evaluate a pinned headless CLI job.

Pen should receive normalized, already-resolved graph data. It should never read
GitHub and decide approval or delivery state itself. Historical decision slices
are outside the Core experiment; supersession is resolved before the current
projection is generated.

## Current repository inputs

The checkout currently has no `.pen` file, Pen package, root Node package, or
Pen CI job. It does have the following reusable inputs:

- the accepted ownership boundary in
  [`ADR-0007`](../../../docs/adr/0007-repository-owned-design-operations-cockpit.md);
- the shared design plan in [`design/roadmap.md`](../../roadmap.md);
- Recipe Detail decisions and explicit supersessions in
  [`decisions/`](../../recipe-detail/decisions/);
- 18 isolated prototype directories under
  [`prototypes/`](../../recipe-detail/prototypes/);
- 117 tracked PNG evidence files, about 10.8 MiB, under
  [`screenshots/`](../../recipe-detail/screenshots/);
- a persistent HTML
  [decision gallery](../../recipe-detail/prototypes/00-decision-gallery/README.md)
  with 12 status cards, links to decisions/prototypes, desktop/mobile checks,
  and a rule to retain superseded evidence.

Those HTML prototypes are executable evidence, but Pen does not officially
document importing HTML as an editable design. Its documented imports are
PNG/JPEG/SVG and Figma; its text schema supports `href`; and image fills can
refer to files relative to the `.pen` file
([import/export](https://docs.pen.dev/core-concepts/import-and-export),
[format](https://docs.pen.dev/for-developers/the-pen-format)). Therefore the
projection can use screenshot thumbnails and links to durable evidence, while
the browser cockpit remains the place that actually runs the HTML journeys.

## Exact Windows and Codex setup path

### Conservative local-MCP path

The project owner uses JetBrains products, and no official JetBrains plugin is
listed in Pen's documentation, downloads, or extension catalog. Use the Windows
x64 desktop app for the first smoke test so JetBrains remains the primary IDE.
The official downloads page offers that desktop build, while the official
troubleshooting page still says the Windows desktop app is unavailable and
recommends VS Code or Cursor. Treat the VS Code extension as a fallback if the
desktop app or its automatic MCP discovery fails
([downloads](https://www.pen.dev/downloads),
[installation](https://docs.pen.dev/getting-started/installation),
[troubleshooting](https://docs.pen.dev/troubleshooting)).

Human steps after a pilot is approved:

1. Copy `%USERPROFILE%\.codex\config.toml` to a safe backup. Pen acknowledges
   that it may modify or duplicate Codex configuration.
2. Install the official Windows x64 Pen desktop app. Keep JetBrains as the
   development IDE; Pen runs as a separate canvas application.
3. Activate Pen with an email address and the emailed code.
4. Follow Pen's documented AI prerequisite: install Claude Code, run `claude`,
   and complete its browser authentication. This requires an Anthropic account.
   The docs list Codex as supported but do not say whether a Codex-only MCP
   session can omit Claude authentication, so this prerequisite must be tested,
   not assumed away
   ([authentication](https://docs.pen.dev/getting-started/authentication)).
5. Open a throwaway `.pen` smoke file outside the repository first, then open
   Codex in the repository and run `/mcp`. If the desktop MCP is not discovered,
   install the `pen.dev` VS Code extension as the documented fallback; its
   marketplace ID still uses the legacy name `highagency.pencildev`.
6. Confirm that an MCP server named `pencil` appears and inspect its actual tool
   names. Perform one read, one bounded insert, one screenshot, one save, and
   confirm that only the smoke file changed.
7. Compare the backed-up Codex config with the current config before creating a
   repository artifact.

The MCP server is app-backed: Pen must be running and a `.pen` file must be open.
Pen says the server starts automatically and locally and publishes no manual
Windows executable path, port, transport, or supported `config.toml` stanza
([AI integration](https://docs.pen.dev/getting-started/ai-integration)). Do not
invent a manual MCP configuration if automatic discovery fails.

### Tools and accounts

| Need | Local MCP | Headless CLI | CI |
| --- | --- | --- | --- |
| Pen activation/account | Email + code | `pen login`: email/password or OTP | Organization with Developer Key |
| Pen client | Windows x64 desktop app; VS Code extension only as fallback | `@pen.dev/cli` | Pinned `@pen.dev/cli` |
| Runtime | Pen client; Codex | Node.js 18+ | Node.js 18+ |
| Agent authentication | Docs currently require authenticated Claude Code even when Codex is the MCP client; omission is unverified | Stored CLI session plus documented Claude model access | `PEN_CLI_KEY` and `ANTHROPIC_API_KEY` |
| Local secret storage | Pen/Claude/Codex-managed user state | `%USERPROFILE%\.pencil\session-cli.json` | CI secret store only |
| Repository secret | None | None | None; never commit keys or sessions |

This checkout already has Node 24 and npm 11, which exceed the CLI's Node 18
minimum. That is an environment observation, not evidence that the Pen package
works here.

## Local MCP versus headless CLI/CI

### Local MCP

Local MCP is the appropriate first path because it keeps a human-visible canvas
open. Codex can read and modify nodes, inspect layout problems, manage variables,
take screenshots, and save while a reviewer observes the result
([AI integration](https://docs.pen.dev/getting-started/ai-integration)). It is
suited to component/layout exploration and visual QA, but not unattended refresh.

### Headless CLI

The current official command contract is:

```powershell
npm install -g @pen.dev/cli
pen version
pen login
pen interactive --in input.pen --out output.pen
```

The CLI uses the same editor engine without a GUI, accepts input/output `.pen`
files, provides an interactive tool shell, runs JSON task batches sequentially,
and exports PNG/JPEG/WEBP/PDF. Its current docs also mention HTML in the low-level
`Export()` operation, but HTML export is not proof of screen-to-screen prototype
interactivity. Headless interactive mode writes only after `save()`
([CLI](https://docs.pen.dev/for-developers/pen-cli)).

The #96 live check pinned `@pen.dev/cli@0.3.4` with
`npm exec --yes --package="@pen.dev/cli@0.3.4" -- pen ...`. The package reports
version `0.3.4`, requires Node `>=22`, and the current checkout has Node
`v24.18.0`. `pen status` and headless interactive mode both require
authentication through `pen login` or `PEN_CLI_KEY`; no offline renderer or
credential-free path was available. This is recorded as a human prerequisite,
not silently replaced with a fake Pen run.

Prompt-driven agent mode is convenient but is the least deterministic path. A
more reviewable pilot would generate normalized data in repository code, use
stable node IDs, and make bounded direct tool operations or Code on Canvas output
rather than ask a model to redraw the whole atlas on every run.

### CI

Pen documents CI agent execution with an organization-scoped `PEN_CLI_KEY` and
`ANTHROPIC_API_KEY`. It does not document an offline CI renderer or a no-account
CI mode. The first CI experiment should therefore be optional and non-blocking:

1. pin the exact package version;
2. load secrets only in the job environment;
3. write to a fresh output path;
4. compare normalized structure and a rendered screenshot against the committed
   projection;
5. upload the diff as evidence without auto-committing it.

Making regeneration a required check is premature until two runs from the same
inputs produce acceptably stable structural and visual results.

## Proposed repository artifacts if a pilot is approved

This is a proposed shape, not a change made by this research:

```text
design/shared/design-graph/                 # authoritative graph, defined elsewhere
design/shared/pen/
  README.md                                 # generated/manual boundary and refresh command
  recipe-detail-overview.pen                # derived spatial projection
  recipe-detail-overview.js                 # deterministic Code on Canvas renderer
  inputs/recipe-detail-projection.json      # normalized generated input, with asOf/source revision
  exports/recipe-detail-overview.png        # optional review snapshot
scripts/design-ops/                         # graph normalization and validation, if approved
```

Do not copy all 117 screenshots into a new Pen asset directory. Use repository-
relative references where Pen supports them and keep each evidence file at its
existing durable path. The normalized input should contain stable IDs,
screen/state/transition relationships, Design and Delivery axes, evidence links,
source selectors, and `asOf`/revision provenance. It should not contain secrets
or hand-maintained copies of live GitHub status.

## Projection pipeline

```text
current decisions + repository graph + cached GitHub snapshot
                         |
                         v
             deterministic normalizer/validator
                         |
              +----------+-----------+
              |                      |
              v                      v
       interactive web cockpit   Pen input JSON
                                      |
                              Code on Canvas / bounded MCP
                                      |
                         .pen atlas + review export
```

Code on Canvas is the strongest deterministic seam. A Script node references a
repository `.js` file relative to the `.pen` file; Pen watches the file and
renders returned layers. Generated children are explicitly derived state,
`Math.random()` is reseeded deterministically, and scripts cannot access the DOM,
network, filesystem, async APIs, or timers. They are limited to 1,000 returned
nodes and two seconds
([Code on Canvas](https://docs.pen.dev/core-concepts/code-on-canvas)). Therefore:

- the normalizer must resolve files, GitHub data, contradictions, and status
  before Pen runs;
- the Pen script receives compact data as declared inputs or generated source;
- the script draws cards, arrows, labels, and thumbnails only;
- HTML prototypes remain links/launch targets in the web cockpit, not code run
  inside Pen.

## Automation and human gates

| Work | Automatable | Human-only or human gate |
| --- | --- | --- |
| Inventory decisions, prototypes, screenshots | Yes; repository scan and schema validation | Confirm which evidence is current versus merely historical |
| Read GitHub task/delivery state | Yes; cache with source URL, revision, and `asOf` | Resolve contradictory sources; never let automation guess |
| Generate graph input and Pen render data | Yes; deterministic ordering and stable IDs | Approve graph semantics and visual grouping |
| Create/update `.pen` layout | Partly; direct MCP/CLI and Code on Canvas | Review hierarchy, readability, and misleading visual implications |
| Link screenshots and prototypes | Yes; validate paths/URLs | Confirm the chosen representative state is useful |
| Visual export and layout checks | Yes; screenshot/export and clipping analysis | Visual acceptance at realistic zoom and density |
| Accounts, email/OTP, Developer Key, CI secrets | No | Human must authenticate and provision/revoke secrets |
| Codex config backup/reconciliation | Comparison can be automated | Human approves any persistent config change |
| Approval, supersession, Design/Delivery status | Derive from authoritative records | Humans create/approve those records; Pen never owns them |

## Parallel work and collision boundaries

After the graph contract is approved, these streams can run in parallel:

- repository inventory/link validator;
- normalized Recipe Detail projection dataset;
- Pen visual component and layout spike on synthetic data;
- local setup/auth smoke test;
- acceptance checklist for structural diff and screenshot review.

The dataset and visual spike converge only after stable IDs and required fields
are fixed. Do not let multiple agents edit the same `.pen` file concurrently.
Pen has no real-time collaboration, no autosave, and recommends Git branches for
collaboration; JSON text does not guarantee a clean semantic merge
([troubleshooting](https://docs.pen.dev/troubleshooting)). If parallel visual
work is necessary, use separate throwaway `.pen` files and have one owner rebuild
the accepted result from the canonical dataset.

## Determinism and reviewability risks

Pen calls `.pen` JSON-based and Git-friendly, and supports branches/diffs
([`.pen` files](https://docs.pen.dev/core-concepts/pen-files),
[Design as Code](https://docs.pen.dev/core-concepts/design-as-code)). Those claims
do not establish reproducible generation:

- the format documentation reserves the right to make breaking changes;
- IDs may be generated when omitted;
- no canonical serializer, key ordering, semantic diff, merge algorithm,
  compatibility window, or byte-for-byte prompt determinism is documented;
- no identical-render guarantee between desktop and headless engines is
  documented;
- autosave is absent and undo/redo is limited;
- Pen documents possible canvas/export mismatches;
- whole-canvas model prompts can rewrite unrelated nodes.

Mitigations to test, not assume: pin CLI/editor versions; emit explicit stable
IDs; sort graph input; isolate generated and hand-edited nodes; prohibit manual
status edits; compare normalized JSON structure rather than raw formatting alone;
render fixed-node screenshots; and reject changes outside an allow-list. Keep a
plain JSON graph and web cockpit usable without Pen so a format change cannot
block the design lifecycle.

## Official naming and documentation inconsistencies

The current command to follow is `npm install -g @pen.dev/cli` and the binary is
`pen`. The former `@pencil.dev/cli` package is marked deprecated on npm with an
instruction to migrate. Nevertheless, official surfaces still expose:

- a live `/for-developers/pencil-cli` page using `@pencil.dev/cli`, `pencil`,
  `PENCIL_CLI_KEY`, and `PENCIL_API_BASE`;
- MCP server name `pencil`;
- token directory `~/.pencil`;
- `pencil_cli_...` as the example value prefix;
- legacy tool names in older package/docs material, while current docs use
  `execute`, `get_app_state`, and operations such as `TakeScreenshot()` and
  `Export()`;
- contradictory Windows desktop availability statements;
- docs that require Claude authentication for AI features while also listing
  Codex as an MCP client.

Sources: [current CLI](https://docs.pen.dev/for-developers/pen-cli),
[stale CLI route](https://docs.pen.dev/for-developers/pencil-cli),
[deprecated npm package](https://www.npmjs.com/package/%40pencil.dev%2Fcli), and
[AI integration](https://docs.pen.dev/getting-started/ai-integration).

The pilot must inspect the installed version and `/mcp` tool schema at runtime;
it should not hard-code a command copied from a stale page.

## V1 data-scope options and effort

These are planning estimates, not vendor claims. They include setup, data
modeling, first render, link/structure checks, one revision, and handoff notes.
They exclude waiting for accounts, procurement, a production-quality GitHub
adapter, and the already-separate web cockpit implementation. Agent time means
active agent execution/review cycles; human time means authentication, decisions,
and visual acceptance. Uncertainty is approximately ±40% because Pen has not
been run in this repository and its current setup/tool naming is transitional.

| Option | Concrete data scope | Agent time | Human time | Primary question answered |
| --- | --- | ---: | ---: | --- |
| **Minimum** | One `.pen` atlas for the 12 current gallery cards; representative screenshot, decision link, prototype link, approved/in-progress label; 3 coarse journeys; no full history or live GitHub adapter | **6–10 h** | **45–90 min** | Can a reviewer navigate the current approved Recipe Detail evidence faster than in the HTML gallery alone? |
| **Core** | Current approved desktop-web slice resolved from the 18 prototype iterations; 20–30 canonical screen/state nodes across read/focus, edit/save/validation/dirty guard, and media/import; transitions; independent Design/Delivery axes from normalized graph snapshot; a small review-selected screenshot set and representative work-item provenance; deterministic renderer and two-run diff test | **16–28 h** | **2–4 h** | Can Pen be a useful, refreshable spatial companion without becoming another status source? |
| **Rich** | All 117 screenshots and 18 prototypes indexed; 50–80 visual nodes; decision/supersession history, blockers, platform/release boundaries, evidence provenance, stale/verification-needed states; overview plus journey/detail frames; pinned CLI export experiment and PR evidence | **40–72 h** | **6–12 h** | Can the projection scale to audit/history use without overwhelming reviewers or producing unreviewable diffs? |

The selected experiment excludes the native-mobile Design evidence. The initial
thumbnail set stays deliberately small, but it is accepted only when the human
reviewer can form a coherent picture of the current desktop interface; image
count alone is not a completion criterion.

The minimum option is intentionally manual-data-assisted and cannot prove
lifecycle synchronization. The selected core option is the smallest one that
tests the architectural claim in ADR-0007. API mappings, complete review/PR
history, and exhaustive screenshot coverage are optional and do not block it.
The rich option should not begin until the core option survives a real source
change and regeneration.

The time and quality thresholds are decision aids, not an automatic verdict.
At each material checkpoint the agent presents the visible result, unexpected
costs or advantages, time spent, and remaining work. The human owner decides
whether to continue, change scope, or stop. The outer planning guide remains
28 agent-hours and 4 human-hours, including no more than 90 minutes of human
setup; an expected steady-state refresh should fit within 30 agent-minutes and
10 minutes of human review.

## Recommended execution ordering, without an adoption decision

1. **Freeze the contract first.** Approve graph fields, source precedence,
   stable IDs, Design/Delivery axes, and the rule that contradictions become
   `verification needed`.
2. **Run a no-repository smoke test.** Back up Codex config, activate the VS Code
   extension, verify `pencil` through `/mcp`, record installed versions/tool
   schema, and remove the smoke file.
3. **Choose one scope option explicitly.** Minimum demonstrates presentation;
   core tests the intended architecture; rich tests scale.
4. **Generate normalized input and the web view first.** This proves that source
   resolution works without Pen.
5. **Build the Pen projection from the same input.** Prefer Code on Canvas and
   bounded operations with stable IDs over whole-atlas prompts.
6. **Run two identical-input regenerations.** Review raw diff, normalized
   structure, fixed screenshots, link validity, and unexpected files.
7. **Change one real source fact.** Regenerate and measure agent time, human
   review time, unrelated diff noise, and whether the correct node changes.
8. **Only after those results, evaluate CLI/CI.** The current local check uses
   `@pen.dev/cli@0.3.4`; authenticate only in the provider flow, keep the job
   optional, and never let it push generated changes.
9. **Make the adoption decision separately.** Evidence should include measured
   maintenance cost, reviewer comprehension, config impact, and exit/rebuild
   cost if Pen's format or pricing changes.

## Source index and unresolved facts

Primary Pen sources checked on 2026-08-20:

- [Downloads](https://www.pen.dev/downloads)
- [Installation](https://docs.pen.dev/getting-started/installation)
- [Authentication](https://docs.pen.dev/getting-started/authentication)
- [AI integration](https://docs.pen.dev/getting-started/ai-integration)
- [CLI](https://docs.pen.dev/for-developers/pen-cli)
- [`.pen` format](https://docs.pen.dev/for-developers/the-pen-format)
- [`.pen` files](https://docs.pen.dev/core-concepts/pen-files)
- [Design as Code](https://docs.pen.dev/core-concepts/design-as-code)
- [Code on Canvas](https://docs.pen.dev/core-concepts/code-on-canvas)
- [Import/export](https://docs.pen.dev/core-concepts/import-and-export)
- [Troubleshooting](https://docs.pen.dev/troubleshooting)
- [Deprecated `@pencil.dev/cli` package metadata](https://www.npmjs.com/package/%40pencil.dev%2Fcli)
- [Pricing](https://www.pen.dev/pricing)

Still unresolved without an actual installation:

- whether Codex-only local MCP can work without Claude Code authentication;
- which Windows client path is currently supported in practice;
- exact installed MCP tool names and config mutation;
- byte-stability and rendering stability across repeated runs;
- behavior of local/repository-relative `href` targets in the viewer;
- whether current free access includes the needed CLI/organization keys and what
  unpublished limits apply. The pricing page says only that Pen is currently
  free and may introduce paid features later.
