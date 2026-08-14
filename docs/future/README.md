# Future Capabilities

This directory is the canonical capture and refinement space for product ideas, technical debt, compatibility leftovers, and intentional deferrals outside the active first-version roadmap. It is not an implementation queue.

The inventory is organized by capability or area rather than by the origin label "technical debt" versus "idea". Keep that single organizing axis while work is only being captured. The refinement task [#33](https://github.com/starkovalera/recipe-manager/issues/33) will decide whether a second classification is useful after the inventory has been audited.

## Funnel

```text
Captured → Investigating → Refining → Ready to promote → Promoted
```

- **Captured** — the opportunity or follow-up is retained with enough context to avoid losing it.
- **Investigating** — facts, feasibility, policy, or product value are being established.
- **Refining** — scope, decisions, dependencies, and acceptance boundaries are being resolved.
- **Ready to promote** — the capability has enough definition to generate prefixed issues.
- **Promoted** — active `[DESIGN]` and/or `[DEV]` issues link back here; this document remains the rationale and refinement record.

Future Capabilities do not receive implementation issues before promotion. Use [`../agents/planning.md`](../agents/planning.md) when promotion occurs.

## Maintenance

When a phase or subphase is completed, add newly discovered follow-up work to the matching capability document while the context is still available. Preserve the current behavior, evidence, reason for deferral, and the next refinement question. If an item does not fit an existing capability, add a new document and an index row rather than recreating a monolithic backlog.

During refinement, keep the item here until its disposition is explicit: promote it, fold it into the active roadmap, mark it as already delivered/current contract, supersede it, or remove it as obsolete. Only then create bounded executable issues.

## Capability index

| Capability | Stage | Target track after promotion | Primary refinement need |
| --- | --- | --- | --- |
| [YouTube video import](youtube-video-import.md) | Investigating | `[DESIGN][IMPORTS]`, `[DEV][BACKEND]` | Validate product value, current provider/policy constraints, retention, and integration against the evolved import architecture |
| [Import and AI evolution](import-and-ai.md) | Captured | Design and Development | Refine prompt/schema cleanup, source-platform behavior, generated covers, evidence handling, and video limits into bounded capabilities |
| [Operations and lifecycle hardening](operations-and-lifecycle.md) | Captured | `[DEV][OPS]` | Separate evidence-triggered operations from speculative complexity and active roadmap requirements |
| [Product expansion](product-expansion.md) | Captured | Design and Development | Refine onboarding, quota, ratings, shared libraries, authors, manual content, and richer media independently |
| [Search evolution](search-evolution.md) | Captured | Design and Development | Establish evaluation data, interaction semantics, and ranking contracts before implementation |
| [List and review UX improvements](list-and-review-ux.md) | Captured | Design and Development | Reconcile tags, ingredients, collections, flags, import history, pagination, and notification improvements with the Core Design Baseline |
