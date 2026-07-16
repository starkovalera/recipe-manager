from openai import OpenAI

from app.core.config import Settings


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings):
        self.model = settings.openai_embedding_model
        self.client = OpenAI(api_key=settings.openai_api_key)

    def embed(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model, input=text)
        return list(response.data[0].embedding)
