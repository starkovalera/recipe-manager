---
status: accepted
---

# Use the selected managed production topology

The initial production topology uses Cloudflare Pages for the React/Vite/PWA client, KrakenD and FastAPI on AWS Lightsail, Neon PostgreSQL with pgvector, AWS SQS/Lambda/EventBridge/S3 for background work and private media, Clerk for identity, Flagsmith for feature flags, and OpenAI for AI capabilities. This combination keeps the API service simple while moving durable state and bursty background processing to managed services; changes to this topology require an explicit replacement decision.
