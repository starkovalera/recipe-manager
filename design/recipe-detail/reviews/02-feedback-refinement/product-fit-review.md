# Product-Fit Review — Feedback Refinement

Status: Proposed for approval  
Updated: 2026-07-22

## Fit

- The recipe remains usable when import flags exist; review is contextual, not a blocking workflow.
- Bulk flag review matches the product meaning of flags as general import messages and anticipates the planned bulk backend update.
- Resource grouping exposes the primary/derived relationship already available in product data without presenting technical provenance terminology.
- Cascade confirmation represents the actual business rule: deleting a primary resource removes its derived resources except the current cover.
- Focus stays deliberately simple and avoids implying portion calculations or cooking-session state that are outside scope.

## Guardrails

- Do not turn resource groups into an asset-management product inside Recipe Detail.
- Do not infer that marking flags reviewed validates specific recipe fields.
- Do not show `Original source` when several primary resources may exist.
- Do not promise restoration for removed resources.
