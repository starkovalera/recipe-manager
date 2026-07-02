from app.imports.url_loaders.generic import GenericUrlContentLoader
from app.imports.url_loaders.registry import UrlContentLoaderRegistry, normalize_import_url


def test_normalize_import_url_accepts_http_and_https():
    assert str(normalize_import_url(" https://example.com/recipe ").value) == "https://example.com/recipe"


def test_normalize_import_url_rejects_non_http():
    result = normalize_import_url("file:///etc/passwd")

    assert result.error_code == "INVALID_URL"


def test_registry_uses_generic_fallback():
    registry = UrlContentLoaderRegistry([GenericUrlContentLoader()])

    loader = registry.loader_for(normalize_import_url("https://example.com").value)

    assert isinstance(loader, GenericUrlContentLoader)
