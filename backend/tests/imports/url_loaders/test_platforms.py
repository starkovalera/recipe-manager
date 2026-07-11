import json

from app.imports.source_loading.types import SecondaryResourceKind, SecondaryResourceLoadStatus
from app.imports.source_loading.url_loaders import InstagramUrlContentLoader
from app.imports.source_loading.url_loaders.threads import ThreadsUrlContentLoader


class FakeResponse:
    def __init__(self, content: bytes, content_type: str = "text/html"):
        self.content = content
        self.headers = {"content-type": content_type, "content-length": str(len(content))}


def instagram_embed_html(media: dict) -> bytes:
    context = json.dumps({"gql_data": {"shortcode_media": media}})
    escaped = json.dumps(context)[1:-1]
    return f'<html><script>"contextJSON":"{escaped}"</script></html>'.encode()


async def test_instagram_loader_parses_embed_sidecar_and_normalizes_url():
    seen_urls: list[str] = []

    async def fetch(url: str, max_bytes: int) -> FakeResponse:
        seen_urls.append(url)
        if url.startswith("https://cdn.test/"):
            return FakeResponse(f"bytes:{url}".encode(), "image/jpeg")
        return FakeResponse(
            instagram_embed_html(
                {
                    "owner": {"username": "chef"},
                    "edge_media_to_caption": {"edges": [{"node": {"text": "Pasta recipe"}}]},
                    "edge_sidecar_to_children": {
                        "edges": [
                            {
                                "node": {
                                    "display_resources": [
                                        {"src": "https://cdn.test/small.jpg", "config_width": 100, "config_height": 100},
                                        {"src": "https://cdn.test/large.jpg", "config_width": 1000, "config_height": 800},
                                    ]
                                }
                            },
                            {
                                "node": {
                                    "is_video": True,
                                    "video_url": "https://cdn.test/video.mp4",
                                    "display_resources": [
                                        {"src": "https://cdn.test/poster.jpg", "config_width": 640, "config_height": 640}
                                    ],
                                }
                            },
                            {
                                "node": {
                                    "display_resources": [{"src": "https://cdn.test/second.jpg", "config_width": 500, "config_height": 500}]
                                }
                            },
                        ]
                    },
                }
            )
        )

    loader = InstagramUrlContentLoader(fetch=fetch)

    assert loader.supports("https://www.instagram.com/p/abc/?utm_source=x")
    assert loader.supports("https://www.instagram.com/reel/abc/")
    assert not loader.supports("https://www.instagram.com/chef/")

    loaded = await loader.load("https://www.instagram.com/chef/p/abc/?utm_source=x", max_images=3, max_image_bytes=1000)

    assert seen_urls[0] == "https://www.instagram.com/p/abc/embed/captioned/"
    assert loaded.url == "https://www.instagram.com/p/abc/"
    assert loaded.text == "Pasta recipe"
    assert loaded.author_name == "chef"
    assert [(image.url, image.position) for image in loaded.images] == [
        ("https://cdn.test/large.jpg", 0),
        ("https://cdn.test/second.jpg", 1),
    ]
    assert [(video.url, video.poster_url, video.position, video.original_name) for video in loaded.videos] == [
        ("https://cdn.test/video.mp4", "https://cdn.test/poster.jpg", 0, "video.mp4")
    ]


async def test_instagram_loader_reports_detected_image_failure_without_aborting():
    async def fetch(url: str, max_bytes: int) -> FakeResponse:
        if url.startswith("https://cdn.test/"):
            return FakeResponse(b"not image", "text/plain")
        return FakeResponse(
            instagram_embed_html(
                {
                    "owner": {"username": "chef"},
                    "edge_media_to_caption": {"edges": [{"node": {"text": "Pasta recipe"}}]},
                    "display_resources": [{"src": "https://cdn.test/bad.jpg", "config_width": 900, "config_height": 900}],
                }
            )
        )

    loaded = await InstagramUrlContentLoader(fetch=fetch).load(
        "https://www.instagram.com/p/abc/",
        max_images=1,
        max_image_bytes=1000,
    )

    assert loaded.images == []
    assert len(loaded.resource_results) == 1
    assert loaded.resource_results[0].kind == SecondaryResourceKind.IMAGE
    assert loaded.resource_results[0].status == SecondaryResourceLoadStatus.FAILED
    assert loaded.resource_results[0].url == "https://cdn.test/bad.jpg"


async def test_instagram_loader_does_not_create_url_text_fallback_for_missing_caption():
    async def fetch(url: str, max_bytes: int) -> FakeResponse:
        return FakeResponse(
            instagram_embed_html(
                {
                    "owner": {"username": "chef"},
                    "edge_media_to_caption": {"edges": []},
                    "display_resources": [],
                }
            )
        )

    loaded = await InstagramUrlContentLoader(fetch=fetch).load(
        "https://www.instagram.com/p/abc/",
        max_images=1,
        max_image_bytes=1000,
    )

    assert loaded.text is None


async def test_instagram_loader_falls_back_to_generic_content_on_embed_error():
    async def fetch(url: str, max_bytes: int) -> FakeResponse:
        if url.endswith(".jpg"):
            return FakeResponse(b"image", "image/jpeg")
        return FakeResponse(
            b'<html><meta property="og:description" content="Fallback caption"><meta property="og:image" content="/fallback.jpg"></html>'
        )

    loaded = await InstagramUrlContentLoader(fetch=fetch).load("https://www.instagram.com/p/missing/", max_images=1, max_image_bytes=1000)

    assert loaded.text == "Fallback caption"
    assert loaded.images[0].url == "https://www.instagram.com/fallback.jpg"


async def test_threads_loader_extracts_primary_same_author_chain_and_media():
    async def fetch(url: str, max_bytes: int) -> FakeResponse:
        if url.startswith("https://cdn.test/"):
            return FakeResponse(f"bytes:{url}".encode(), "image/webp")
        payload = {
            "postID": "root-pk",
            "data": {
                "edges": [
                    {
                        "node": {
                            "thread_items": [
                                {
                                    "post": {
                                        "pk": "root-pk",
                                        "code": "abc",
                                        "user": {"id": "u1", "username": "chef"},
                                        "caption": {"text": "First part"},
                                        "image_versions2": {
                                            "candidates": [
                                                {"url": "https://cdn.test/root-small.webp", "width": 100, "height": 100},
                                                {"url": "https://cdn.test/root-large.webp", "width": 800, "height": 800},
                                            ]
                                        },
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "node": {
                            "thread_items": [
                                {
                                    "post": {
                                        "pk": "second-pk",
                                        "code": "def",
                                        "user": {"id": "u1", "username": "chef"},
                                        "caption": {"text": "Second part"},
                                        "carousel_media": [
                                            {
                                                "video_versions": [{"url": "https://cdn.test/video.mp4"}],
                                                "image_versions2": {
                                                    "candidates": [{"url": "https://cdn.test/poster.webp", "width": 400, "height": 400}]
                                                },
                                            },
                                            {
                                                "image_versions2": {
                                                    "candidates": [{"url": "https://cdn.test/carousel.webp", "width": 500, "height": 500}]
                                                }
                                            },
                                        ],
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "node": {
                            "thread_items": [
                                {
                                    "post": {
                                        "pk": "reply-pk",
                                        "code": "ghi",
                                        "user": {"id": "u2", "username": "other"},
                                        "caption": {"text": "Other reply"},
                                        "image_versions2": {
                                            "candidates": [{"url": "https://cdn.test/reply.webp", "width": 900, "height": 900}]
                                        },
                                    }
                                }
                            ]
                        }
                    },
                ]
            },
        }
        return FakeResponse(f'<html><script type="application/json">{json.dumps(payload)}</script></html>'.encode())

    loader = ThreadsUrlContentLoader(fetch=fetch)

    assert loader.supports("https://www.threads.net/@chef/post/abc")
    assert loader.supports("https://www.threads.com/t/abc")
    assert not loader.supports("https://www.threads.net/@chef")

    loaded = await loader.load("https://www.threads.com/@chef/post/abc?x=1", max_images=5, max_image_bytes=1000)

    assert loaded.url == "https://www.threads.com/@chef/post/abc"
    assert loaded.author_name == "chef"
    assert loaded.text == "First part\n\nSecond part"
    assert [(image.url, image.position) for image in loaded.images] == [
        ("https://cdn.test/root-large.webp", 0),
        ("https://cdn.test/carousel.webp", 1),
    ]
    assert [(video.url, video.poster_url, video.position, video.original_name) for video in loaded.videos] == [
        ("https://cdn.test/video.mp4", "https://cdn.test/poster.webp", 0, "video.mp4")
    ]


async def test_threads_loader_uses_decoded_meta_description_when_json_post_is_missing():
    async def fetch(url: str, max_bytes: int) -> FakeResponse:
        return FakeResponse(
            b'<html><meta property="og:description" content="Recipe &amp; details"><script type="application/json">{}</script></html>'
        )

    loaded = await ThreadsUrlContentLoader(fetch=fetch).load("https://www.threads.net/t/abc", max_images=2, max_image_bytes=1000)

    assert loaded.text == "Recipe & details"
    assert loaded.images == []


async def test_threads_loader_reports_image_failure_without_discarding_caption():
    async def fetch(url: str, max_bytes: int) -> FakeResponse:
        if url.startswith("https://cdn.test/"):
            return FakeResponse(b"not-image", "text/plain")
        payload = {
            "postID": "root-pk",
            "data": {
                "edges": [
                    {
                        "node": {
                            "thread_items": [
                                {
                                    "post": {
                                        "pk": "root-pk",
                                        "code": "abc",
                                        "user": {"id": "u1", "username": "chef"},
                                        "caption": {"text": "Recipe caption"},
                                        "image_versions2": {
                                            "candidates": [{"url": "https://cdn.test/bad.webp", "width": 800, "height": 800}]
                                        },
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
        }
        return FakeResponse(f'<html><script type="application/json">{json.dumps(payload)}</script></html>'.encode())

    loaded = await ThreadsUrlContentLoader(fetch=fetch).load(
        "https://www.threads.com/@chef/post/abc",
        max_images=1,
        max_image_bytes=1000,
    )

    assert loaded.text == "Recipe caption"
    assert loaded.images == []
    assert len(loaded.resource_results) == 1
    assert loaded.resource_results[0].kind == SecondaryResourceKind.IMAGE
    assert loaded.resource_results[0].status == SecondaryResourceLoadStatus.FAILED
