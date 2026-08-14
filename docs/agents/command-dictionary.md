# Agent Command Dictionary

Updated: 2026-08-14
Status: active workspace convention
Owner: `AGENTS.md` points here; [`task-lifecycle.md`](task-lifecycle.md) owns
the lifecycle sequence.

This document defines the short command protocol for this repository. The
commands are a compact way to select a known workflow; they do not replace the
task contract, issue acceptance criteria, or human approval gates.

## Recognition and target resolution

Recognize a command only when the first non-empty line of the user message
starts with `#` followed by a lowercase command slug:

```text
#<command> [optional target or arguments]
```

The command token must match `[a-z][a-z0-9-]*`. `#23` is an issue reference,
and `# Heading` is a Markdown heading, not a command. Treat an inline `#word`
as ordinary user text. Process one command per message; ask before guessing
when a message is ambiguous.

When no target is supplied, use the current repository, worktree, branch,
active issue, and open PR. An explicit issue number, PR number, or GitHub URL
takes precedence. If more than one issue or PR matches, stop and ask which one
is in scope.

Natural-language `merged` messages and links to merged PRs remain lifecycle
signals. They are handled by [`task-lifecycle.md`](task-lifecycle.md); they are
not additional command tokens.

## Commands

### `#rebase-main [target]`

Refresh `origin/main` and compare it with the current feature branch. If main
advanced, rebase the branch, rerun the affected checks, and update its open PR
with `git push --force-with-lease`. If main is already an ancestor, report a
no-op. Preserve a dirty worktree, stop on conflicts, and never use an
unconditional force push. If no PR is open, update only the branch and report
that no PR was available to update.

### `#lifecycle [target]`

Read the current lifecycle and determine the active stage for the target task.
Execute every applicable, safe step; verify human prerequisites and stop at a
human gate, approval gate, conflict, or unresolved scope question. At the
post-merge stage, follow the merge verification, documentation consistency
check, and conditional issue-closure rules in lifecycle section 9.

### `#status [target]`

Inspect, without guessing, the current worktree, repository and branch, local
versus `origin/main`, PR base/head/state/checks, issue state/assignees/labels,
native blockers, and the applicable lifecycle stage. This is a read-only status
check until it verifies that the relevant PR is merged. A verified merged PR is
a trigger to continue the post-merge lifecycle; it does not bypass merge
verification, the documentation consistency check, acceptance criteria, or
the conditional issue-closure rule. If the PR is not merged, report that and
keep post-merge completion unchanged.

### `#refactor [scope]`

Read the repository refactoring guide and inspect the requested or current
scope for a small, behavior-preserving improvement. First return the proposed
refactor, affected invariants, and verification plan. Wait for explicit user
approval before editing. After approval, implement only the approved change and
rerun the affected checks.

### `#next [target]`

Analyze the current task, lifecycle stage, issue graph, blockers, open PR, and
human prerequisites. Return the next executable task or decision, why it is
next, and what remains blocked. This command is analysis-only; it does not
create issues, edit files, close tasks, or start implementation.

### `#cmd [command]`

List the available commands and their side-effect class. With a command name,
show its target resolution, preconditions, actions, approval requirements, and
completion result format.

## Side effects and approvals

| Command | Default side effect | Approval rule |
| --- | --- | --- |
| `#cmd` | Read-only | None |
| `#status` | Read-only status inspection; a verified merge hands off to lifecycle section 9 | Lifecycle gates still apply |
| `#next` | Read-only analysis | None |
| `#refactor` | Proposal only | Explicit approval before edits |
| `#rebase-main` | Rebase and, when a PR exists, branch push | Stop for dirty state or conflicts |
| `#lifecycle` | Execute applicable lifecycle work, including scoped documentation/issue/PR actions | Stop at human or approval gates |

All commands are repeatable. If the requested state already holds, return a
no-op result with evidence. Do not broaden a command's scope to solve an
unrelated problem.

## Required result format

Every command response should identify:

```text
Command:
Target:
State observed:
Checks:
Actions:
Result:
Blocked or next:
```

The result must distinguish work performed from work that remains blocked or
requires a human action.
