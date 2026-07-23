import pytest

from app.media.presentation import build_media_url


def test_build_media_url_uses_canonical_route_for_prefixed_key() -> None:
    assert build_media_url("imports/derived/owner-1/job-1/image.jpg") == "/media/imports/derived/owner-1/job-1/image.jpg"


def test_build_media_url_rejects_flat_key() -> None:
    with pytest.raises(ValueError, match="canonical"):
        build_media_url("image.jpg")
