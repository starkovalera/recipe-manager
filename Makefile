infra-up:
	docker compose up -d postgres redis

infra-down:
	docker compose down

backend-test:
	cd backend && uv run pytest

frontend-test:
	cd frontend && pnpm test

backend-dev:
	cd backend && uv run fastapi dev app/main.py

worker-dev:
	cd backend && uv run dramatiq app.imports.tasks

frontend-dev:
	cd frontend && pnpm dev
