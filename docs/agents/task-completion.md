# Development Task Completion Checkpoint

Run this checkpoint after the task's requested behavior and focused verification are complete, before final handoff. Report each applicable result in the issue or pull request.

## Backend refactoring review

Required when backend production or backend test code changed.

1. Read [`../refactoring-guidelines.md`](../refactoring-guidelines.md).
2. Re-check the touched workflow against its business invariants, public contracts, persistence behavior, side effects, error layers, transaction boundaries, external boundaries, and lifecycle types.
3. Inspect the changed area for avoidable duplication, unclear ownership, hidden side effects, unnecessary abstractions, scattered dependent decisions, broad stage objects, obsolete compatibility paths, and tests coupled to deleted structure.
4. Perform the small, behavior-preserving local refactor needed to leave the completed scope maintainable.
5. Remove obsolete code, imports, tests, and compatibility paths exposed by that refactor.
6. Re-run focused tests and every broader relevant check required by changed shared behavior or contracts.
7. Re-check invariants and public contracts after refactoring.
8. Report one outcome:
   - refactoring performed, with the affected responsibility and verification;
   - no refactoring needed, with the inspected area and reason;
   - larger refactoring identified and left out of scope, with its invariants and verification boundary proposed for a separate approved issue.

Keep this checkpoint local to the completed task. A broad redesign requires its own scope, blockers, acceptance criteria, and approval.

## Extending this checkpoint

Add future project-wide completion requirements here. Development issues should keep one stable link to this document rather than copying the checklist.
