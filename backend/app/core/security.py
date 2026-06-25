import uuid


def client_id_from_header(raw_client_id: str | None) -> str:
    normalized = raw_client_id.strip() if raw_client_id else ""
    if not normalized:
        return f"anonymous-{uuid.uuid4()}"
    return normalized[:128]
