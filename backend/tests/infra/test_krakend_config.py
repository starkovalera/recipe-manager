import json
from pathlib import Path

from app.main import create_app

SUPPORTED_METHODS = {"get", "post", "put", "patch", "delete"}
EXTRA_GATEWAY_ROUTES = {
    ("/openapi.json", "GET"),
    ("/docs", "GET"),
    ("/docs/oauth2-redirect", "GET"),
    ("/redoc", "GET"),
}
PUBLIC_ROUTES = EXTRA_GATEWAY_ROUTES | {("/health", "GET"), ("/webhooks/clerk", "POST")}


def _krakend_root() -> Path:
    return Path(__file__).resolve().parents[3] / "infra" / "krakend"


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _routes() -> list[dict]:
    return json.loads((_krakend_root() / "config" / "endpoints.json").read_text(encoding="utf-8"))["items"]


def _openapi_routes() -> set[tuple[str, str]]:
    return {
        (path, method.upper())
        for path, operations in create_app().openapi()["paths"].items()
        for method in operations
        if method in SUPPORTED_METHODS
    }


def test_flexible_config_routes_cover_fastapi_contract_once():
    configured = [(route["endpoint"], route["method"]) for route in _routes()]

    assert len(configured) == len(set(configured))
    assert set(configured) == _openapi_routes() | EXTRA_GATEWAY_ROUTES
    assert {
        pair for pair in configured if next(route for route in _routes() if (route["endpoint"], route["method"]) == pair)["public"]
    } == PUBLIC_ROUTES


def test_flexible_config_enforces_jwt_without_forwarding_authorization():
    template = (_krakend_root() / "krakend.tmpl").read_text(encoding="utf-8")

    assert '"auth/validator"' in template
    assert 'env "CLERK_JWKS_URL"' in template
    assert 'env "CLERK_ISSUER"' in template
    assert '["sub", {{ marshal $.auth.subject_header }}]' in template
    assert 'propagate_claims": [["sub", {{ marshal $.auth.subject_header }}]]' in template
    assert "issuer_header" not in template
    input_headers = template.split('"input_headers": [', 1)[1].split("]", 1)[0]
    assert "Authorization" not in input_headers


def test_identity_headers_are_not_browser_controlled_cors_headers():
    template = (_krakend_root() / "krakend.tmpl").read_text(encoding="utf-8")
    cors_headers = template.split('"allow_headers": [', 1)[1].split("]", 1)[0]

    assert "X-Authenticated-Subject" not in cors_headers
    assert '"Authorization"' in cors_headers


def test_gateway_forwards_svix_signature_headers_to_public_webhook():
    template = (_krakend_root() / "krakend.tmpl").read_text(encoding="utf-8")
    input_headers = template.split('"input_headers": [', 1)[1].split("]", 1)[0]

    assert '"Svix-Id"' in input_headers
    assert '"Svix-Timestamp"' in input_headers
    assert '"Svix-Signature"' in input_headers


def test_static_gateway_config_was_removed():
    assert not (_krakend_root() / "krakend.json").exists()


def test_compose_diagnostics_do_not_require_clerk_but_gateway_startup_does():
    compose = (_repository_root() / "docker-compose.yml").read_text(encoding="utf-8")
    entrypoint = (_krakend_root() / "entrypoint.sh").read_text(encoding="utf-8")

    assert "CLERK_ISSUER: ${CLERK_ISSUER:-}" in compose
    assert "CLERK_JWKS_URL: ${CLERK_JWKS_URL:-}" in compose
    assert "${CLERK_ISSUER:?" not in compose
    assert "${CLERK_JWKS_URL:?" not in compose
    assert "${CLERK_ISSUER:?" in entrypoint
    assert "${CLERK_JWKS_URL:?" in entrypoint
