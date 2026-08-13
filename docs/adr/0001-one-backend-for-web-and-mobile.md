---
status: accepted
---

# Use one backend and API contract for web and mobile

Recipe Manager uses one backend and one owner-scoped HTTP API for responsive web and native mobile clients. Separate client experiences may use platform-specific interaction patterns, but creating a second mobile backend would duplicate domain rules, identity boundaries, and lifecycle behavior without product benefit.
