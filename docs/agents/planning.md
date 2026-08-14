# Planning and Issue Conventions

Use [`../roadmap.md`](../roadmap.md) to orient any project-planning task. Detailed current scope lives in the Design and Development roadmaps linked there; GitHub issues are the executable work queue.

## Track prefixes

Every active issue title starts with exactly one global track prefix:

- `[DESIGN]` — decisions, research, prototypes, reviews, and baseline integration;
- `[DEV]` — backend, web, mobile, infrastructure, authentication, operations, and verification implementation.

Add one controlled area prefix when it improves scanning:

| Design | Development |
| --- | --- |
| `[SHARED]` | `[BACKEND]` |
| `[AUTH]` | `[FRONTEND]` |
| `[RECIPES]` | `[MOBILE]` |
| `[IMPORTS]` | `[INFRA]` |
| `[COLLECTIONS]` | `[AUTH]` |
| `[NOTIFICATIONS]` | `[OPS]` |
| `[ACCOUNT]` | |
| `[ADMIN]` | |

Design issues add a platform qualifier after the area when the output belongs to one client:

- `[WEB]` for responsive web;
- `[MOBILE]` for the native mobile client.

Use no platform qualifier for shared product contracts, cross-platform constraints, or final reconciliation.

Examples:

```text
[DESIGN][RECIPES] Approve Recipe Edit instructions behavior
[DESIGN][RECIPES][WEB] Design Recipe Edit instructions
[DESIGN][RECIPES][MOBILE] Design Recipe Edit instructions
[DEV][INFRA] Bootstrap remote Terraform state and GitHub OIDC
```

Extend this vocabulary here before using a new area prefix.

## Relationships

- Parent/sub-issue relationships express scope containment only.
- Native `blocked by` relationships express execution gates.
- Phase or list order does not create a blocker by itself.
- An issue with all blockers closed is on the executable frontier.

Keep containment and blocking visually distinct in diagrams and issue descriptions.

## Work hierarchy

Use four levels and do not hand an epic to one agent as though it were an executable issue:

1. A roadmap milestone states a release outcome.
2. A parent issue or epic contains one bounded workstream.
3. An executable child issue fits one agent context, one branch, and one independently verifiable outcome.
4. A checklist inside that child records tightly coupled steps in the same delivery slice.

Sub-issues express containment. Add native blockers only between executable children that truly cannot proceed in parallel.

## Readiness

Use the default triage labels without adding a separate refinement label:

| Condition | Label | Required next step |
| --- | --- | --- |
| Scope, inputs, acceptance criteria, and blockers are complete; no external user action is required | `ready-for-agent` | Assign one executable child issue to an agent |
| A user must approve a decision, create an account/project, supply credentials, accept billing, or perform another external action | `ready-for-human` | Record the exact action and the evidence that unblocks the issue |
| Scope or decisions are incomplete | `needs-triage` | Run refinement and replace open questions with decisions and acceptance criteria |
| Required facts are missing from the requester | `needs-info` | Ask only for the missing facts |

An issue with an open blocker is not on the executable frontier even if its own text is otherwise complete.

## Design issues

A Design Domain uses a shared-contract child, separate `[WEB]` and `[MOBILE]` children, and a reconciliation child. The platform children may proceed in parallel after their actual shared blockers close. The reconciliation child verifies continuity without forcing identical interfaces.

A Design issue resolves one bounded decision or produces one reviewable evidence increment. It names the Design Domain, affected shared decisions, target platform, required states, approval criterion, and evidence destination. Parallel Design work is allowed when real blockers permit it; Core baseline integration reconciles shared decisions across every domain before approval.

An unresolved decision map remains `needs-triage` until its children are executable. A Design issue may begin as `ready-for-agent` when the next outcome is an evidence packet or bounded prototype, then move to `ready-for-human` when approval is the next action.

## Development issues

A Development issue is a narrow, independently verifiable tracer bullet. It delivers one observable outcome, declares real blockers, and includes tests at the highest stable seam. Prefer vertical slices; use expand-contract only for changes that cannot remain green as vertical slices.

Apply `ready-for-agent` only when scope, contracts, acceptance criteria, and blockers are complete.

Every Development issue includes this acceptance criterion:

```markdown
- [ ] Complete the shared [`Development Task Completion Checkpoint`](../agents/task-completion.md), including the backend refactoring review when backend code changed.
```

Reference the shared checkpoint instead of copying its current steps into each issue. Expanding the checkpoint then applies consistently to existing tasks.

## Future capabilities

Future Capabilities live under [`../future/`](../future/README.md), not as active implementation issues. Promotion requires a refined scope, decisions, dependencies, acceptance boundary, and target track. Create prefixed issues only after promotion, then link them back to the capability document.

For the shorthand requests “добавь в todo”, “добавь в туду”, or “add to todo”, follow the canonical capture rule in the root [`AGENTS.md`](../../AGENTS.md): write the item into the matching `docs/future/*.md` capability document and keep [#33](https://github.com/starkovalera/recipe-manager/issues/33) as the umbrella refinement task. Do not interpret the shorthand as an automatic request to create an active issue.
