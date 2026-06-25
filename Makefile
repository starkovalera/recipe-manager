backend-test:
	cd backend && uv run pytest

frontend-test:
	cd frontend && pnpm test

backend-dev:
	cd backend && uv run fastapi dev app/main.py

frontend-dev:
	cd frontend && pnpm dev
