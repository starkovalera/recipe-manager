from app.imports.url_loaders.platforms import FixturePlatformLoader


class ThreadsUrlContentLoader(FixturePlatformLoader):
    allowed_hosts = {"threads.net", "www.threads.net", "threads.com", "www.threads.com"}
