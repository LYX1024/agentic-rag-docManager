"""OpenAI-compatible embedding API client."""
from openai import OpenAI
from loguru import logger


class EmbeddingClient:
    """OpenAI-compatible embeddings client. Works with any OpenAI-compatible API."""

    def __init__(self, base_url: str, api_key: str, model: str, dimension: int = 1536):
        self.model = model
        self.dimension = dimension
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        logger.info(f"EmbeddingClient: model={model}, base_url={base_url}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts. Returns list of embedding vectors."""
        if not texts:
            return []

        resp = self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        embeddings = [d.embedding for d in resp.data]
        return embeddings

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        result = self.embed_documents([query])
        return result[0]
