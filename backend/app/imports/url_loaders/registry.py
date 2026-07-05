from app.imports.url_loaders.types import UrlContentLoader


class UrlContentLoaderRegistry:
    def __init__(self, loaders: list[UrlContentLoader]):
        self.loaders = loaders

    def loader_for(self, url: str) -> UrlContentLoader:
        for loader in self.loaders:
            if loader.supports(url):
                return loader
        raise ValueError(f"No URL loader for {url}")
