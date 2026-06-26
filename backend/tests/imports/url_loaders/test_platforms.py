from app.imports.url_loaders.instagram import InstagramUrlContentLoader
from app.imports.url_loaders.threads import ThreadsUrlContentLoader


class FakeResponse:
    def __init__(self, content: bytes, content_type: str = "text/html"):
        self.content = content
        self.headers = {"content-type": content_type, "content-length": str(len(content))}


async def fetch_instagram(url: str, max_bytes: int) -> FakeResponse:
    if url.endswith(".jpg"):
        return FakeResponse(b"image", "image/jpeg")
    return FakeResponse(
        b'''
        <script type="application/json" id="recipe-manager-fixture">
        {
          "caption": "Pasta recipe",
          "authorName": "chef",
          "media": [
            {"type": "image", "url": "https://cdn.test/1.jpg"},
            {"type": "video", "url": "https://cdn.test/v.mp4", "posterUrl": "https://cdn.test/poster.jpg"},
            {"type": "image", "url": "https://cdn.test/2.jpg"}
          ]
        }
        </script>
        '''
    )


async def test_instagram_loader_supports_posts_and_skips_videos_as_images():
    loader = InstagramUrlContentLoader(fetch=fetch_instagram)

    assert loader.supports("https://www.instagram.com/p/abc/")
    loaded = await loader.load("https://www.instagram.com/p/abc/", max_images=5, max_image_bytes=1000)

    assert loaded.text == "Pasta recipe"
    assert loaded.author_name == "chef"
    assert [image.url for image in loaded.images] == ["https://cdn.test/1.jpg", "https://cdn.test/2.jpg"]


async def fetch_threads(url: str, max_bytes: int) -> FakeResponse:
    if url.endswith(".jpg"):
        return FakeResponse(b"image", "image/jpeg")
    return FakeResponse(
        b'''
        <script type="application/json" id="recipe-manager-fixture">
        {
          "caption": "Threaded soup recipe",
          "authorName": "chef",
          "media": [{"type": "image", "url": "https://threads.test/1.jpg"}]
        }
        </script>
        '''
    )


async def test_threads_loader_supports_threads_net_and_com():
    loader = ThreadsUrlContentLoader(fetch=fetch_threads)

    assert loader.supports("https://www.threads.net/@chef/post/abc")
    assert loader.supports("https://www.threads.com/@chef/post/abc")
    loaded = await loader.load("https://www.threads.com/@chef/post/abc", max_images=1, max_image_bytes=1000)

    assert loaded.text == "Threaded soup recipe"
    assert loaded.images[0].url == "https://threads.test/1.jpg"
