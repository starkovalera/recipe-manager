---
status: accepted
---

# Validate identity at the gateway and authorize in the backend

KrakenD validates Clerk identity and forwards only trusted identity context; FastAPI owns user resolution, fixed roles, capabilities, owner scoping, and domain authorization. This preserves one backend-authoritative authorization model while avoiding duplicate JWT validation and provider coupling inside domain handlers.
