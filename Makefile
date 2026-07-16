infra-up:
	docker compose up -d --build postgres redis krakend

infra-down:
	docker compose down

backend-test:
	cd backend && uv run pytest

frontend-test:
	cd frontend && pnpm test

backend-dev:
	cd backend && uv run fastapi dev app/main.py --host 127.0.0.1 --port 8010

worker-dev:
	cd backend && uv run dramatiq app.worker

frontend-dev:
	cd frontend && pnpm dev

gateway-check:
	docker build --target validator -t recipe-manager-krakend-check ./infra/krakend

gateway-up:
	docker compose up -d --build krakend

gateway-down:
	docker compose stop krakend

gateway-logs:
	docker compose logs -f krakend
