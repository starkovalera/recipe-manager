# Refactoring Guidelines

These guidelines are the default standard for refactoring work in this project. Apply them during implementation and at the completion checkpoint of every phase, subphase, or iteration.

## Preserve Behavior First

- Identify the affected business invariants, public contracts, persistence behavior, and side effects before changing structure.
- Treat refactoring as behavior-preserving unless a behavior change is explicitly planned and approved.
- Keep the blast radius narrow. Do not use a local refactor as a reason to redesign unrelated parts of the system.
- When a business rule changes, update the invariant checklist and tests explicitly rather than hiding the change inside structural work.

## Build Readable Workflows

- Long scenarios should read from top to bottom as a sequence of meaningful business stages.
- Each stage should have clear inputs, outputs, dependencies, and side effects.
- Extract conceptual steps, repeated operations, or genuinely confusing details.
- Do not create one-line or one-call helpers that only rename an obvious expression or forward a call.
- Prefer clarity and predictable control flow over minimizing line count.

## Keep Related Decisions Local

- Keep logically dependent operations next to each other when all required data is already available.
- Derive downstream values immediately after the value they depend on instead of separating them with unrelated calls or control flow.
- Convert temporary booleans, intermediate classifications, and branching results into their final domain values as early as practical.
- After the final dependent values are derived, stop carrying or re-reading the temporary decision variable through later stages.
- A decision may be deferred only when it genuinely requires data produced by a later stage, a different transaction, or an external operation.
- Prefer one visually complete decision block over several fragments that require a reader to reconstruct the relationship across a function or module.

## Keep Responsibilities Separate

- Do not mix API handling, business decisions, persistence, external integrations, serialization, logging, notifications, storage, and queue orchestration in one logical block.
- Keep routers and workers thin. Domain behavior should remain callable independently of HTTP and queue infrastructure.
- Organize modules around coherent responsibilities, but do not create one file per function.
- Make side effects visible. A caller should be able to tell whether an operation writes to the database, saves a file, publishes work, or only transforms data.

## Avoid Unnecessary Abstractions

- Add a protocol, registry, service, context, or generic helper only when it represents real variability, repeated use, or a stable boundary.
- Do not create abstractions only to reduce parameter count or make the code appear layered.
- Keep protocols and abstract types in one ownership location within their domain and reuse them from there.
- Remove obsolete helpers, adapters, compatibility paths, and parallel implementations after migration.
- If intentionally dormant code remains for future work, document why it exists and that it is not currently used.

## Use Context Objects Deliberately

- A context object should contain one coherent set of data that must travel through several stages.
- Do not use a context object as a container for unrelated local variables or to hide function dependencies.
- Prefer direct parameters when dependencies are local and the resulting signature remains readable.
- Prefer immutable snapshots when data must cross transaction, session, worker, or external-call boundaries.

## Make Data Stages Explicit

- Use distinct concepts and types for raw input, normalized input, external-service input, external-service output, domain data, and persisted models.
- Names should communicate the lifecycle stage and intended use of the data.
- Avoid reusing one broad object across stages when its meaning or guarantees change.
- Apply a business rule in the stage that owns the resulting decision. Do not hide review, persistence, or status decisions inside unrelated normalization.

## Protect External Boundaries

- Use a consistent internal naming and typing style. Adapt external naming through schemas, aliases, and serializers at the boundary.
- Keep validation/deserialization separate from serialization/output behavior.
- Keep external provider schemas separate from domain and persistence models when their responsibilities differ.
- Do not let external API field names or provider-specific details spread through business logic.

## Model Errors by Layer

- Separate user-facing API errors from domain, import-stage, provider, and infrastructure errors.
- Raise concrete error types with stable categories and default messages instead of assembling arbitrary code/message/status combinations at call sites.
- Translate internal errors to HTTP responses only at the API boundary.
- Preserve useful diagnostic context and exception chaining without exposing internal details to users.
- Keep retryable and non-retryable failures distinguishable where background processing is involved.

## Type Lifecycle State

- Represent statuses, event types, notification types, error categories, roles, and other closed sets with enums or equivalent constrained types.
- Do not scatter magic strings or duplicate status values across services, workers, tests, and frontend contracts.
- Enforce important lifecycle constraints at the database level when practical.
- Keep high-level persisted state separate from detailed diagnostic state.

## Keep Transactions Explicit

- A transaction should cover one understandable atomic operation.
- Do not keep a database session or transaction open during long external calls, media processing, or AI work.
- Do not pass live ORM objects between independent sessions. Pass identifiers, immutable snapshots, or typed data instead.
- Load and mutate an ORM object inside the session that owns the operation.
- Failure status, audit events, and notifications must survive rollback of the failed primary operation when the product requires durable diagnostics.
- Use foreign keys and ORM relationships for real entity relationships instead of synchronizing parallel identifiers manually.

## Centralize Cross-Cutting Operations

- Use one implementation for repeated event creation, notification creation, error mapping, query filtering, serialization, and structured logging patterns.
- Prefer structured logs with stable messages and separately bound context fields.
- Bind repeated operation context once rather than rebuilding it for every log message.
- Keep diagnostics useful without letting logging obscure the main business flow.

## Keep Test Code Outside Production

- Put fake providers, test builders, dependency overrides, and monkeypatch helpers in test modules or fixtures.
- Do not add production branches whose only purpose is to support tests.
- Provide normal dependency seams in production and override them from tests.

## Test Behavior, Not Obsolete Structure

- Add focused unit tests for independent stages and regression tests for corrected behavior.
- Use integration tests for API, database, worker, and persistence boundaries.
- Test business invariants, outputs, errors, state transitions, and side effects rather than internal call sequences.
- Remove tests that exist only for deleted helpers or obsolete architecture.
- Keep test fixtures and expectations aligned with the current domain model.

## Refactor Iteratively

After each refactoring iteration:

1. Remove obsolete code, imports, tests, and compatibility paths.
2. Check naming, typing, formatting, module ownership, and locality of logically dependent decisions.
3. Run focused tests for the affected behavior.
4. Run the full relevant test suite when shared behavior or contracts changed.
5. Re-check business invariants and public contracts.
6. Record any intentional temporary solution in the future-work document.
7. Confirm whether another small local cleanup is needed before review.

Do not expand a phase-completion cleanup into a broad redesign. If a larger refactor is needed, add it to the plan, define its invariants and verification scope, and request approval before implementation.
