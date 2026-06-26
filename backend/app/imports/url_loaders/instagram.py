from app.imports.url_loaders.platforms import FixturePlatformLoader


class InstagramUrlContentLoader(FixturePlatformLoader):
    allowed_hosts = {"instagram.com", "www.instagram.com"}
