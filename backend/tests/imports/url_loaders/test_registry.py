from app.imports.url_loaders.generic import GenericUrlContentLoader
from app.imports.url_loaders.registry import UrlContentLoaderRegistry


def test_registry_uses_generic_fallback():
    registry = UrlContentLoaderRegistry([GenericUrlContentLoader()])

    loader = registry.loader_for("https://example.com")

    assert isinstance(loader, GenericUrlContentLoader)
