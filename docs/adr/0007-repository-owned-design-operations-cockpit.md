---
status: accepted
---

# Generate Design Operations views from a repository-owned graph

Recipe Manager will keep the structure of its Design Operations view in a
machine-readable repository-owned graph and generate an interactive web cockpit
from that graph, the existing decision gallery, HTML prototypes, and current
GitHub/decision evidence. The cockpit is the primary human navigation surface;
Pen may provide a derived spatial overview from the same inputs, but neither Pen
nor its exports own approval, task, or delivery status.

This avoids creating a manually maintained third source of truth while retaining
clickable journeys and a panoramic visual map. GitHub owns task, blocker, and
delivery state; current design decisions own approvals and supersessions; tracked
prototypes and screenshots remain evidence under
[ADR-0005](0005-prototypes-are-design-evidence.md). The graph stores stable IDs,
relationships, and source selectors rather than copied mutable status, and
contradictions render as needing verification instead of being guessed.

The graph, generated cockpit, and any Pen projection are Design tooling, not
production application source. A task that changes their represented state must
generate and verify the final view in the same pull request before merge;
post-merge lifecycle work only audits that atomic result. A bounded Core Pen
experiment is approved, but Pen adoption and implementation of the complete
graph, cockpit, and lifecycle checks remain separate decisions.
