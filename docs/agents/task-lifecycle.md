# Agent Task Lifecycle

Use this sequence for every repository task that changes files or produces a project artifact. Answer-only and status-only requests do not require a branch or pull request. The user may explicitly choose another workflow; record that exception in the task.

This document owns the order of work. Detailed rules remain in the linked planning, issue-tracker, refactoring, design, and completion documents.

## 1. Establish scope and a fresh base

Before changing files:

1. Read the root and nearest applicable `AGENTS.md` files.
2. Identify the workstream: application implementation, product design, design-to-implementation, or documentation/maintenance.
3. Read the task or issue, the current roadmap, and the relevant contracts and decision documents.
4. Fetch the latest `origin/main`.
5. Inspect the worktree before changing refs and preserve unrelated changes. If the task changes cannot be separated safely, stop and report the conflict before editing.
6. Unless the user explicitly names another base or Git flow, create or switch to a feature branch from the fresh `origin/main`. Use the repository's `codex/<scope>` branch convention unless the user specifies another name.
7. Verify the branch and base after switching; do not silently carry unrelated changes into the task.

**Done when:** the task scope, applicable instructions, base SHA, feature branch, and any pre-existing changes are known and recorded in the task context.

## 2. Close implementation questions before coding

Read the task against the current behavior and contracts. Make an explicit list of unresolved questions covering behavior, interfaces, invariants, persistence, external boundaries, verification, dependencies, and human prerequisites.

If any unanswered question could change the implementation, acceptance criteria, architecture, or required human action, pause implementation and run the local [`grill-with-docs`](../../.agents/skills/grill-with-docs/SKILL.md) session. That skill runs a `/grilling` session with `/domain-modeling`. Do not replace an unavailable or failed session with invented assumptions: report the missing prerequisite and ask how to proceed.

Before implementation resumes, record the session's decisions, rejected alternatives, remaining boundaries, and acceptance consequences in the appropriate project documentation and in the task or issue. Use `CONTEXT.md`, an ADR, a design decision, or the task specification according to [`domain.md`](domain.md) and the task's workstream.

If no implementation questions remain, state that the existing task contract is sufficient and identify the assumptions being carried forward.

**Done when:** no implementation-blocking question remains, and every decision produced by clarification is findable from the task and its canonical documentation.

## 3. Present the contract and plan

Before implementation, present the user with:

- the contract: scope, inputs, outputs, invariants, state or persistence effects, public interfaces, errors, side effects, and acceptance criteria;
- the plan: ordered work blocks, touched areas, dependencies, verification, documentation updates, and the expected result;
- any assumptions or decisions that need explicit approval.

Use [`planning.md`](planning.md) for issue hierarchy, readiness, blockers, and acceptance conventions. Pause for approval when an open decision would materially change the requested scope or contract.

**Done when:** the user has received a concrete contract and plan, the execution boundary is understood, and every required approval is either recorded or obtained.

## 4. Surface human actions

Identify actions that only a human can perform before or after the task: approvals, credentials, account or provider setup, billing, external configuration, manual device checks, deployment, review, or merge.

Tell the user about required pre-task actions before implementation. If such an action blocks execution, record the exact action and evidence needed to unblock it and use the readiness conventions in [`planning.md`](planning.md). Tell the user about post-task actions in the completion handoff and in the pull request.

**Done when:** every human prerequisite is either completed, explicitly assigned, or recorded as a non-blocking follow-up with an owner and trigger.

## 5. Implement the scoped work

Implement only the approved contract. Preserve unrelated worktree changes, keep production and design boundaries intact, and update task-specific source-of-truth documents when the work changes a decision, contract, or operational rule.

Prefer the highest stable verification seam for the workstream. Do not turn a prototype, mock, or design artifact into production code without an approved design-to-implementation scope.

**Done when:** the requested behavior or artifact is complete, the changed scope matches the approved contract, and no untracked implementation assumption is carrying the result.

## 6. Verify and review refactoring

After implementation:

1. Run focused checks and every broader relevant check required by changed shared behavior or contracts. Apply the verification rules in the root `AGENTS.md`.
2. Read and apply [`refactoring-guidelines.md`](../refactoring-guidelines.md). Inspect the touched area for a small, behavior-preserving refactor; perform it when it improves the completed scope, then rerun the affected checks.
3. Run the shared [`task-completion.md`](task-completion.md) checkpoint before handoff. Backend production or backend test changes require its backend refactoring review. If a larger refactor is identified, keep it out of the current scope, record its invariants and verification boundary, and route it as separate approved work.
4. Re-check the contract, business invariants, public interfaces, and documentation links after any refactoring.

Report the verification results and the refactoring outcome in the task or pull request: refactoring performed, no refactoring needed with the inspected boundary, or larger refactoring left for separate work.

**Done when:** all applicable checks pass, the completion checkpoint is recorded, and the refactoring decision is explicit and evidence-backed.

## 7. Review naturally discovered future work

Inspect the completed work for technical debt, intentional deferrals, or product ideas that arose naturally while solving the task. Do not invent backlog items or expand the task to speculative improvements.

If a candidate exists, describe its evidence, current behavior, reason to defer, and next refinement question to the user. After the user approves the capture, update the matching canonical document under [`docs/future/`](../future/README.md) and its index when needed. Follow the capture and promotion rules in the root `AGENTS.md` and [`planning.md`](planning.md); do not create an active issue merely because an item was captured.

If no natural candidate exists, report that no future item was discovered.

**Done when:** every naturally discovered candidate is either approved and captured in the canonical future documentation or explicitly reported as awaiting approval, and speculative items have not been added.

## 8. Publish the completed task

Before creating or updating a pull request, perform a final base-freshness check even if `origin/main` was fetched at the start of the task:

1. Fetch the latest `origin/main`.
2. Check whether `origin/main` is an ancestor of the feature branch (`git merge-base --is-ancestor origin/main HEAD`).
3. If it is not an ancestor, rebase the feature branch onto `origin/main` before creating or updating the pull request. Resolve any conflicts, rerun the affected verification, and use `git push --force-with-lease` when the rebase rewrites the published branch.

For repository changes, create or update a commit, push the feature branch, and open or update a draft pull request after the completion checks. The user may explicitly request a different publication mode or ask to keep the work local; that instruction wins.

The pull request should link the task and summarize the contract, delivered result, verification, refactoring outcome, human actions, future-work disposition, and documentation impact. Keep the PR draft unless the user explicitly asks for a ready-for-review PR.

**Done when:** the feature branch and PR contain exactly the intended changes, the PR has the verification and handoff information, and the local worktree status is known.

## 9. Synchronize documentation after merge

When the user says that the task is ready and the PR is merged, verify the actual GitHub merge state before marking the work complete. If it is not merged, report the discrepancy and keep completion status unchanged.

After merge:

1. Fetch the latest `origin/main` and create a documentation-maintenance branch if the updates are not already part of the merged PR.
2. Update the owning detailed roadmap, architecture or design documents, and every document where the plan steps or task links are reflected.
3. Update the corresponding node and status in [`docs/roadmap.md`](../roadmap.md), mark the completed work with `✓`, and record the concrete result.
4. Update the target architecture diagram when an open architecture decision closed, and update unresolved questions when the merged result answers or changes them.
5. Refresh issue links and execution status without duplicating GitHub's native blocker or acceptance data.
6. Publish these documentation-maintenance changes through the normal PR flow when a new change is required.

**Done when:** the merged result, roadmap, detailed planning documents, architecture/design records, task links, completion marks, and open-question lists agree, with no stale plan step presented as current work.

## Source-of-truth map

| Concern | Authoritative document |
| --- | --- |
| Scope, readiness, blockers, issue hierarchy | [`planning.md`](planning.md) and the GitHub issue |
| Issue operations and native dependencies | [`issue-tracker.md`](issue-tracker.md) |
| Domain terminology and decisions | [`domain.md`](domain.md), `CONTEXT.md`, and applicable ADR/design documents |
| Refactoring standard | [`refactoring-guidelines.md`](../refactoring-guidelines.md) |
| Completion checkpoint | [`task-completion.md`](task-completion.md) |
| Future-work capture and promotion | [`future/README.md`](../future/README.md) and the root `AGENTS.md` |
| Human project roadmap and post-merge status | [`roadmap.md`](../roadmap.md) |
