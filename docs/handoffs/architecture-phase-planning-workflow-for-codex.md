# Instructions for Codex: Architecture Phase Planning Workflow

Use this workflow when planning future phases for `starkovalera/recipe-manager`.

You already have repository access and are expected to inspect its current state. Do not repeatedly ask for the repository link, generic project summary, or information available in code and docs.

Your role in a planning chat is to discuss and design one phase, obtain explicit approval, and then produce exactly two final handoff files. Do not implement application code unless the user explicitly changes the task.

## Required planning sequence

For every phase:

1. inspect the current repository, roadmap, affected docs, code, tests, recent merged PRs, inherited deferred work, and relevant open PRs;
2. explain the phase goal, current limitation, desired end state, in-scope work, deferred work, and adjacent systems that must remain unchanged;
3. identify unresolved architectural decisions and edge cases;
4. discuss material decisions with the user one logical question at a time;
5. record approved decisions and do not silently replace them later;
6. present one consolidated final phase summary;
7. wait for explicit approval;
8. after approval, create exactly two handoff files:
   - direct implementation instructions for a future Codex worker;
   - an owner runbook for preparation, manual verification, critical review, and merge.

Do not skip from a roadmap title directly to implementation instructions. Do not create extra protocol, addendum, start, checklist, or helper files unless the user explicitly asks for them. All required execution rules must be embedded in the two phase files.

## Repository inspection

Before discussing architecture:

- read the relevant roadmap item;
- inspect the actual boundary being changed;
- read affected architecture and operational docs;
- inspect existing tests and provider/runtime patterns;
- inspect recent merged PRs for conventions;
- identify stale roadmap assumptions;
- identify concurrent work that must remain separate.

The current repository is authoritative. If an old document conflicts with `main`, point it out.

Summarize only findings relevant to the phase.

## Phase scope discussion

State separately:

- product/operational goal;
- public API contracts;
- application/domain rules;
- ownership and lifecycle;
- provider/infrastructure behavior;
- transaction/retry/idempotency rules;
- frontend implications;
- documentation and comments;
- automated verification;
- owner-performed external/manual verification;
- explicitly deferred work.

Do not hide scope expansion inside implementation details.

## Open questions and edge cases

Actively inspect for unresolved decisions involving:

- request/response shape;
- partial versus whole-operation failure;
- authentication, ownership, and information disclosure;
- lifecycle states;
- retries, idempotency, and duplicate requests;
- transaction and I/O boundaries;
- provider failure mapping;
- inconsistent database/external state;
- batching and N+1 behavior;
- legacy removal and compatibility;
- runtime differences;
- logging/secrets;
- migrations and rollout order;
- deletion and maintenance interactions;
- future extensibility that could be accidentally blocked;
- related future contracts that must remain separate.

Use YAGNI. Do not invent broad abstractions for hypothetical use cases, but avoid fields or boundaries with misleading semantics.

## Decision discussion

For each material issue:

1. explain the concrete problem;
2. provide 2–3 viable approaches when there is a real choice;
3. explain trade-offs;
4. recommend one;
5. wait for the user's decision when it changes architecture, public behavior, security, migration, or scope.

Discuss one logical decision at a time. Do not send a large questionnaire. Do not repeat answered questions.

Maintain an approved-decisions ledger covering:

```text
Goal
In scope
Deferred
Public contracts
Architecture
Domain rules
Ownership/security
Lifecycle
Failure semantics
Provider behavior
Transactions/retries
Performance/batching
Frontend
Documentation/comments
Testing
Manual/external verification
Open questions
```

If a later answer conflicts with an earlier decision, surface the conflict.

## Final summary and approval gate

When no blocking question remains, present a consolidated summary covering all ledger sections and edge cases. Make clear that it is the final design summary, not yet the implementation instruction.

Ask for explicit approval. Approval may be “да”, “approved”, “фиксируем”, or another unambiguous confirmation.

Do not create the two handoff files before approval. If the user requests changes, revise the summary and ask again.

After approval, treat the decisions as fixed. Reopen them only if current repository inspection reveals a literal contradiction; report that contradiction instead of guessing.

## Output: exactly two phase handoff files

Create both under the repository’s established handoff directory, normally:

```text
docs/handoffs/<phase>-<feature>-codex-instructions.md
docs/handoffs/<phase>-<feature>-owner-runbook.md
```

Attach downloadable copies in the chat.

Do not create separate execution protocols, addenda, start files, or duplicated checklists. The implementation workflow belongs inside File A; owner responsibilities belong inside File B.

## File A: instructions for the implementation Codex worker

Write directly to the worker using imperative language. The file must be standalone; the worker must not need the planning conversation.

Include:

- repository and phase context;
- authoritative docs to read;
- exact goal, scope, and deferred work;
- every approved decision;
- public contracts and examples;
- architecture boundaries and data flow;
- ownership, lifecycle, errors, retries, transactions, provider behavior, and performance constraints;
- backend/frontend/gateway implications;
- documentation and required comments;
- complete test matrix;
- exact repository verification commands;
- required diff, scope, architecture, security, and legacy self-audit;
- required PR body and completion-report format;
- owner-performed manual/external verification handoff;
- explicit prohibition on changing approved decisions, expanding scope, or merging the PR.

### Mandatory autonomous execution rules in File A

The implementation worker must perform one readiness check at the beginning.

It verifies repository/origin access, the current base branch, required docs, working state, local tooling, and owner-controlled prerequisites.

If a real blocker exists, it asks the user for the one specific decision or external action required and waits. Valid blockers are limited to:

- literal repository/design contradiction;
- material ambiguity affecting architecture, security, public contract, migration, or scope;
- missing user-controlled prerequisite such as credentials, accounts, keys, test buckets, or cloud actions;
- required scope expansion;
- unauthorized destructive or irreversible action.

If readiness passes, the worker starts immediately and does not ask the user to approve:

- an implementation plan;
- branch name;
- task decomposition or order;
- file choices;
- tests;
- individual commits;
- intermediate results;
- routine next steps.

The worker autonomously creates a feature branch from the current base, implements the entire phase, tests, self-audits, documents, commits, pushes, and opens a draft PR. Progress updates may be informational but never approval gates.

The default review unit is the complete draft PR. The worker does not ask for review of partial commits or unfinished states and never merges the PR.

### Mandatory worker self-audit in File A

Require the worker to:

- run `git diff --check`, diff stat/name list, and branch commit list;
- group and explain every changed file;
- run all backend/frontend/gateway/migration checks with pass counts, skips, warnings, and failures;
- run and classify legacy/security grep searches;
- verify architecture boundaries and security invariants;
- provide exact file/class/function references;
- provide a compact 6–10 item key human-review map;
- state all unperformed checks and exact reasons.

Do not transfer mechanical repository-wide audit to the owner.

## File B: owner runbook

Write for the user, normally in Russian.

Explicitly state the same autonomous interaction model: one readiness check, then implementation through draft PR without per-step confirmation. The owner reviews the completed PR.

Separate responsibilities.

### Codex owns

- feature branch creation;
- implementation and commits;
- all automated tests;
- complete diff/file audit;
- repository-wide grep/search classification;
- architecture/security/boundary audit;
- documentation consistency checks;
- draft PR creation;
- verification report and key human-review map.

### Owner owns

- external credentials, accounts, keys, buckets, cloud-console actions, tunnels, and other prerequisites outside the agent environment;
- browser/device/manual smoke scenarios;
- product and visual behavior;
- review of a small set of critical architecture/API/security decisions identified by Codex;
- verification-gap risk assessment;
- final PR review, ready status, merge, and cleanup.

The runbook must not tell the owner to inspect every changed file, manually classify all grep matches, or independently rerun the complete automated suite unless the user explicitly asks for duplication.

Include:

- exact pre-launch prerequisites and commands;
- what to give Codex;
- valid execution blockers and architecture stop-signs;
- exact verification report expected from Codex;
- critical human-review checklist only;
- detailed manual smoke procedures with terminal separation, commands, test-data preparation, browser steps, expected results, and shutdown commands;
- external/cloud actions;
- automated-only edge cases that the owner should not reproduce manually;
- PR-body expectations;
- merge blockers;
- after-merge steps.

Never reduce File B to “run tests and review the PR.”

## Planning-artifact verification

Before claiming the handoff is complete:

- verify both files exist;
- reread them against the approved summary;
- confirm they agree on scope, contracts, deferred work, and responsibilities;
- confirm File A contains the autonomous readiness/branch/PR workflow directly;
- confirm File B does not require per-step supervision or full mechanical diff review;
- confirm no extra helper/protocol/addendum/start files were created;
- scan for `TBD`, `TODO`, vague “appropriate” handling, and contradictory instructions;
- confirm commands match the current repository.

## End of iteration

After creating and verifying the two files:

1. state their repository paths and branch;
2. attach both files;
3. summarize what each contains;
4. stop before implementation unless the user explicitly asks to execute it.

For the next phase, restart from repository inspection and phase-goal discussion.