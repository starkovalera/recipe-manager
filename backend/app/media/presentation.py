def build_media_url(storage_key: str) -> str:
    if len(storage_key.split("/")) != 5:
        raise ValueError("Media URL requires a canonical storage key.")
    return f"/media/{storage_key}"
