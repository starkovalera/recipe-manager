# Instructions for Codex: Autonomous Implementation Execution Protocol

Apply this protocol together with every phase-specific implementation instruction.

## Start with one readiness check

Before changing code, verify that you have:

- access to the current repository and `origin`;
- the current target base branch and a working tree from which you can create an isolated feature branch;
- the approved design and phase-specific implementation instruction;
- the required local tooling, or the ability to install project dependencies from committed lockfiles;
- no unresolved repository contradiction that makes the approved design impossible;
- no missing owner-controlled prerequisite required before implementation can begin.

If a real blocker exists, stop once and ask the user for the specific decision or external action needed. Wait for that answer before continuing. Do not guess around a blocker.

A valid blocker is limited to:

- a literal contradiction between the approved design and the current repository;
- a material ambiguity with different architecture, security, public-contract, migration, or scope consequences;
- an external prerequisite controlled by the user, such as credentials, an account, a test bucket, a key, or a cloud-console action;
- a required scope expansion;
- a destructive or irreversible action that was not already authorized.

Routine implementation choices are not blockers.

## Continue autonomously when ready

If the readiness check passes, begin immediately. Do not ask the user to approve:

- an implementation plan;
- the feature branch name;
- task decomposition or execution order;
- individual files or refactors within the approved scope;
- test cases;
- each commit;
- intermediate implementation results;
- the next routine step.

You may provide concise progress updates, but do not turn them into approval gates.

Autonomously perform the complete workflow:

1. update repository refs and confirm the intended base;
2. create a dedicated feature branch from the current base branch;
3. inspect the relevant production code, tests, and documentation;
4. implement the entire approved phase;
5. add and run all required tests;
6. perform the complete diff, scope, architecture, security, and legacy-flow self-audit required by the phase instruction;
7. update documentation and required code comments;
8. commit the work in intentional commits;
9. push the feature branch;
10. open a draft PR against the approved base branch;
11. provide the PR, verification evidence, verification gaps, and key human-review map to the user.

The user reviews the complete draft PR rather than supervising every substep.

## Questions during implementation

Ask the user only when a valid blocker from the readiness section appears later during implementation.

When asking:

- state the exact contradiction or missing prerequisite;
- explain why continuing would require guessing or violating the approved scope;
- present only the concrete decision or action needed;
- do not bundle routine progress updates into the question.

After the blocker is resolved, continue autonomously to the draft PR.

## Pull request boundary

Open a draft PR at the end of implementation. Do not merge it.

Do not ask the user to review partial commits or unfinished intermediate states unless the user explicitly requests that workflow. The default review unit is the complete draft PR with fresh verification evidence.
