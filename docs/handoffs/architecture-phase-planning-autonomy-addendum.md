# Addendum for Codex: Autonomous Execution in Future Phase Handoffs

Apply this addendum together with `docs/handoffs/architecture-phase-planning-workflow-for-codex.md`.

When you prepare the two final handoff files for any future approved phase, make the implementation-worker instruction explicitly require the following default workflow:

1. The worker performs one readiness check at the beginning.
2. The worker verifies repository access, the intended base branch, required documents, tools, and owner-controlled prerequisites.
3. If a real blocker exists, the worker asks for one specific decision or external action and waits.
4. If no blocker exists, the worker starts immediately without asking for another plan approval.
5. The worker creates the feature branch autonomously.
6. The worker implements, tests, self-audits, documents, commits, and pushes without requesting approval for each substep.
7. The worker asks questions only for:
   - a literal repository/design contradiction;
   - a material architecture, security, public-contract, migration, or scope ambiguity;
   - a missing owner-controlled prerequisite;
   - an unauthorized destructive or irreversible action;
   - a required scope expansion.
8. The worker opens a draft PR and returns the complete PR for one consolidated user review.
9. The worker never merges the PR.

Routine implementation choices, file selection, test additions, branch naming, task ordering, and commits are not approval gates.

The owner runbook must describe the same interaction model. It must not ask the user to supervise individual steps. It should reserve the user's work for external prerequisites, browser/manual checks, critical diff review, verification-gap assessment, and final PR review/merge.

For implementation, instruct the future worker to read `docs/handoffs/codex-autonomous-execution-protocol.md` together with the phase-specific implementation instruction.
