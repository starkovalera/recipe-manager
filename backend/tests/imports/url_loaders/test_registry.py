from app.imports.source_loading.url_loaders import GenericUrlContentLoader
from app.imports.source_loading.url_loaders.registry import UrlContentLoaderRegistry


def test_registry_uses_generic_fallback():
    registry = UrlContentLoaderRegistry([GenericUrlContentLoader()])

    loader = registry.loader_for("https://example.com")

    assert isinstance(loader, GenericUrlContentLoader)
