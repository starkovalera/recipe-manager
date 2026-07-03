import hashlib

from app.embeddings.constants import EMBEDDING_DIMENSIONS


class FakeEmbeddingProvider:
    model = "fake-embedding"

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        while len(values) < EMBEDDING_DIMENSIONS:
            for byte in digest:
                values.append((byte / 255.0) * 2 - 1)
                if len(values) == EMBEDDING_DIMENSIONS:
                    break
            digest = hashlib.sha256(digest).digest()
        return values
