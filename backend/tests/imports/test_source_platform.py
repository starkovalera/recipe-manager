from app.imports.source_platform import derive_source_name, detect_source_name_from_url
from app.models import SourceName


def test_detect_source_name_from_url_detects_known_platforms():
    assert detect_source_name_from_url("https://www.instagram.com/p/abc") == SourceName.INSTAGRAM
    assert detect_source_name_from_url("https://threads.net/@cook/post/abc") == SourceName.THREADS
    assert detect_source_name_from_url("https://www.threads.com/@cook/post/abc") == SourceName.THREADS
    assert detect_source_name_from_url("https://www.tiktok.com/@cook/video/1") == SourceName.TT


def test_detect_source_name_from_url_falls_back_to_other():
    assert detect_source_name_from_url("https://example.com/recipe") == SourceName.OTHER
    assert detect_source_name_from_url("not a url") == SourceName.OTHER


def test_derive_source_name_matches_reference_behavior():
    assert derive_source_name([]).source_name == SourceName.MANUAL
    assert derive_source_name(["https://instagram.com/p/abc"]).source_name == SourceName.INSTAGRAM
    assert derive_source_name(["https://www.threads.com/@cook/post/abc"]).source_name == SourceName.THREADS
    assert derive_source_name(["https://example.com/recipe"]).source_name == SourceName.OTHER


def test_derive_source_name_fails_for_mixed_known_platforms():
    result = derive_source_name(["https://instagram.com/p/abc", "https://threads.net/@cook/post/abc"])

    assert result.ok is False
    assert result.error_code == "MIXED_SOURCE_PLATFORMS"
