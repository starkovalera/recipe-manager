# YouTube Video Import

Stage: Investigating
First-version scope: excluded
Last investigation: 2026-07

## Opportunity

Import a public YouTube recipe video into the existing Recipe Manager import pipeline while preserving evidence, attribution, diagnostics, and resource lifecycle constraints.

This is a parallel future investigation. It does not block Core Design Baseline v1, technical production, or Public v1.

## Existing investigation

Draft PR [#5](https://github.com/starkovalera/recipe-manager/pull/5) explored a two-stage approach:

```text
YouTube metadata and validation
  → Gemini structured VideoEvidence
  → existing OpenAI recipe extraction
  → existing Recipe and Import Job lifecycle
```

It also explored direct YouTube URL forms, duration/confidence gates, description fallback, unchanged thumbnail covers, evidence events and telemetry, expiry metadata, later cleanup and cover refresh, and a public-launch compliance review.

Treat those findings as investigation input, not an approved current spec. They were written against an older repository state and provider/policy snapshot.

## Refinement questions

- Is YouTube import valuable enough to justify provider, quota, latency, and retention complexity?
- Which current YouTube forms, availability states, and duration limits are supported?
- Is the two-stage Gemini-evidence/OpenAI-recipe approach still preferable to direct extraction?
- Which provider models and structured-output contracts are current and supportable?
- Which source material may be retained, for how long, and with what refresh/deletion behavior?
- How is thumbnail/media attribution presented across web and mobile?
- Which failures fall back to description or other evidence, and which terminate the Import Job?
- What policy and compliance review is required before non-private use?
- How does the capability fit the current queue, storage, media-access, and maintenance contracts?

## Promotion boundary

Before promotion:

- refresh provider/API and policy research from primary sources;
- inspect current import, queue, storage, media, and maintenance contracts;
- approve user journeys and attribution/failure UX;
- define resource lifecycle and operational cost boundaries;
- define an end-to-end acceptance matrix and real blockers;
- decide whether delivery remains one capability or splits into import, cleanup, and cover-refresh milestones.

After refinement, generate `[DESIGN][IMPORTS]` and/or `[DEV][BACKEND]` issues and link them here. Close or supersede draft PR #5 once its durable findings are fully represented in this space.
