# Future Capabilities

This space holds product and technical possibilities outside the active first-version roadmap. A Future Capability is refined here before it becomes executable Design or Development work.

## Funnel

```text
Captured → Investigating → Refining → Ready to promote → Promoted
```

- **Captured** — the opportunity is retained with a clear motivation.
- **Investigating** — facts, feasibility, policy, or product value are being established.
- **Refining** — scope, decisions, dependencies, and acceptance boundaries are being resolved.
- **Ready to promote** — the capability has enough definition to generate prefixed issues.
- **Promoted** — active `[DESIGN]` and/or `[DEV]` issues link back here; this document remains their rationale and refinement record.

Future Capabilities are not part of the active frontier and do not receive implementation issues before promotion. Use [`../agents/planning.md`](../agents/planning.md) when promotion occurs.

## Capability index

| Capability | Stage | Target track after promotion | Primary refinement need |
| --- | --- | --- | --- |
| [YouTube video import](youtube-video-import.md) | Investigating | `[DESIGN][IMPORTS]`, `[DEV][BACKEND]` | Validate product value, current provider/policy constraints, retention, and integration against the evolved import architecture |
| [Import and AI evolution](import-and-ai.md) | Captured | Design and Development | Group prompt, source-platform, generated-cover, Telegram, Reels/Shorts, author-link, and video-limit opportunities into coherent capabilities |
| [Operations and lifecycle hardening](operations-and-lifecycle.md) | Captured | `[DEV][OPS]` | Separate evidence-triggered operations from speculative complexity and active roadmap requirements |
| [Product expansion](product-expansion.md) | Captured | Design and Development | Refine onboarding, quota, ratings, shared libraries, authors, manual content, and richer media independently |
| [Search evolution](search-evolution.md) | Captured | Design and Development | Establish evaluation data, interaction semantics, and ranking contracts before implementation |
| [List and review UX improvements](list-and-review-ux.md) | Captured | Design and Development | Reconcile tags, collections, flags, import history, pagination, and notification improvements with the Core Design Baseline |

The archived monolithic backlog is preserved at [`../archive/product/2026-07-future-work-backlog.md`](../archive/product/2026-07-future-work-backlog.md). New refinement belongs in the capability documents above, not in the archive.
