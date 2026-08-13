# Search Evolution

Stage: Captured
First-version scope: excluded unless separately promoted

## Opportunities

- multiple simultaneous structured chips with explicit within/across-type semantics;
- stronger tag-concept suggestions without silently rewriting free text;
- clearer Search Debug explanations for structured, semantic, and mixed queries;
- deterministic derived semantic labels from structured recipe fields;
- versioned embedding-input rules and recomputation;
- strict numeric filters after UX approval;
- lightweight query-concept suggestions;
- a manual evaluation set with expected good and bad results;
- later query expansion and hybrid ranking based on evidence;
- Search Debug pagination;
- direct navigation when autocomplete resolves one concrete Recipe.

## Promotion boundary

Build the evaluation set and approve query/chip interaction semantics before ranking changes. Any promoted implementation must preserve owner scoping, stable pagination, explainability, embedding invalidation, and deterministic tests.
