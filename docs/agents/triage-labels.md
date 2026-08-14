# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

Edit the right-hand column to match whatever vocabulary you actually use.

## Release-version labels

`v1` and `v2` are orthogonal planning labels, not readiness states:

| Label | Meaning |
| --- | --- |
| `v1` | The first web-only production release, including its shared contracts, web Design/Development, infrastructure, operations, security, and release evidence. |
| `v2` | The post-V1 mobile client sequence, beginning with a dedicated mobile planning iteration and covering all mobile Development work. |

Keep one of these labels on active release-scoped issues when the target is
known. Paired mobile Design work may remain in the V1 product context while
being non-blocking for V1; a mobile-only Development issue belongs to `v2`.
Always retain the applicable canonical triage label separately.
