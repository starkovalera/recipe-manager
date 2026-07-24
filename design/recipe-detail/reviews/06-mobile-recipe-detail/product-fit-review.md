# Product-fit review

Status: internal pass; user approval pending.

Compared normal, imported-with-flags, manual, no-cover, dense, long, loading, failed, and missing product states.

- Every imported recipe can expose neutral Import info; the action has no warning icon.
- Recipes without flags keep the normal Default View, while flagged recipes add only a compact review status.
- Source identity and cooking facts are separate; Default View exposes no visible Source or Author labels.
- Tags and Collections are bounded to two visible values plus an accurate `+N` disclosure.
- Import Info contains flags, grouped resources, ignored resources when present, and role-gated Debug details; it excludes Extracted result, Provenance, Original source, Restore, and per-field resolution.
- Removing a primary resource removes non-cover derivatives while explicitly retaining the current cover; resource deletion copy says the saved recipe is unchanged.

Remaining risk: actual backend bulk flag updates and primary/derived relationship payloads still need implementation contracts outside this design artifact.
