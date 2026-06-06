"""OpenAI-compatible embedding API client."""
from openai import OpenAI
from loguru import logger


class EmbeddingClient:
    """OpenAI-compatible embeddings client. Works with any OpenAI-compatible API."""

    def __init__(self, base_url: str, api_key: str, model: str, dimension: int = 1536):
        self.model = model
        self.dimension = dimension
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=120.0)
        logger.info(f"EmbeddingClient: model={model}, base_url={base_url}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts in batches. Returns list of embedding vectors."""
        if not texts:
            return []

        batch_size = 8
        all_embeddings = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"Embedding batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}: {len(batch)} texts")
            for attempt in range(3):
                try:
                    resp = self.client.embeddings.create(
                        model=self.model,
                        input=batch,
                    )
                    batch_embeddings = [d.embedding for d in resp.data]
                    all_embeddings.extend(batch_embeddings)
                    break
                except Exception as e:
                    if attempt < 2:
                        logger.warning(f"Embedding retry {attempt + 1}: {e}")
                        import time
                        time.sleep(2)
                    else:
                        logger.error(f"Embedding batch failed after 3 attempts: {e}")
                        raise

        return all_embeddings

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        result = self.embed_documents([query])
        return result[0]
