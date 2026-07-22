def build_media_url(storage_key: str) -> str:
    if "/" in storage_key:
        return f"/media/{storage_key}"
    return f"/legacy-media/{storage_key}"
