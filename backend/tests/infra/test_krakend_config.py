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
UPSTREAM_HOST = "http://host.docker.internal:8010"
REQUIRED_CORS_HEADERS = {
    "accept",
    "authorization",
    "content-type",
    "idempotency-key",
    "range",
    "x-client-id",
}
REQUIRED_INPUT_HEADERS = REQUIRED_CORS_HEADERS | {
    "if-modified-since",
    "if-none-match",
    "user-agent",
}


def _load_gateway_config() -> dict:
    project_root = Path(__file__).resolve().parents[3]
    with (project_root / "infra" / "krakend" / "krakend.json").open(encoding="utf-8") as config_file:
        return json.load(config_file)


def _openapi_routes() -> set[tuple[str, str]]:
    return {
        (path, method.upper())
        for path, operations in create_app().openapi()["paths"].items()
        for method in operations
        if method in SUPPORTED_METHODS
    }


def test_krakend_routes_cover_the_complete_fastapi_contract():
    config = _load_gateway_config()
    configured_routes = [(endpoint["endpoint"], endpoint["method"]) for endpoint in config["endpoints"]]

    assert len(configured_routes) == len(set(configured_routes))
    assert set(configured_routes) == _openapi_routes() | EXTRA_GATEWAY_ROUTES


def test_krakend_routes_are_transparent_single_backend_proxies():
    config = _load_gateway_config()

    for endpoint in config["endpoints"]:
        assert endpoint["output_encoding"] == "no-op"
        assert endpoint["input_query_strings"] == ["*"]
        assert REQUIRED_INPUT_HEADERS <= {header.lower() for header in endpoint["input_headers"]}
        assert len(endpoint["backend"]) == 1

        backend = endpoint["backend"][0]
        assert backend["encoding"] == "no-op"
        assert UPSTREAM_HOST in backend["host"]
        assert backend["method"] == endpoint["method"]
        assert backend["url_pattern"] == endpoint["endpoint"]


def test_krakend_service_and_cors_settings_match_local_topology():
    config = _load_gateway_config()
    extra_config = config["extra_config"]
    cors = extra_config["security/cors"]

    assert config["version"] == 3
    assert config["port"] == 8080
    assert extra_config["router"]["auto_options"] is True
    assert {"http://127.0.0.1:5173", "http://localhost:5173"} <= set(cors["allow_origins"])
    assert REQUIRED_CORS_HEADERS <= {header.lower() for header in cors["allow_headers"]}
    assert "*" in cors["allow_headers"]
