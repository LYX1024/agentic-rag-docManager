"""OpenAI-compatible async embedding API client."""
import asyncio
import time as time_mod
from openai import AsyncOpenAI
from loguru import logger


class EmbeddingClient:
    """Async OpenAI-compatible embeddings client."""

    def __init__(self, base_url: str, api_key: str, model: str, dimension: int = 1536):
        self.model = model
        self.dimension = dimension
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=120.0)
        logger.info(f"EmbeddingClient: model={model}, base_url={base_url}")

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed texts in batches with retry. Async."""
        if not texts:
            return []

        batch_size = 8
        all_embeddings = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            logger.info(f"Embedding batch {batch_num}/{total_batches}: {len(batch)} texts")
            for attempt in range(3):
                try:
                    resp = await self.client.embeddings.create(model=self.model, input=batch)
                    all_embeddings.extend([d.embedding for d in resp.data])
                    break
                except Exception as e:
                    if attempt < 2:
                        logger.warning(f"Embedding retry {attempt + 1}: {e}")
                        await asyncio.sleep(2)
                    else:
                        logger.error(f"Embedding batch failed after 3 attempts: {e}")
                        raise

        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string. Async."""
        result = await self.embed_documents([query])
        return result[0]
