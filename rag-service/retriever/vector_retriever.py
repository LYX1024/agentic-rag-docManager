"""Vector retriever using embedding + FAISS similarity search."""
from loguru import logger


class VectorRetriever:
    """Vector-based retriever wrapping kb_service.search() with embedding."""

    def __init__(self, kb_service, embedding_client):
        """Initialize the vector retriever.

        Args:
            kb_service: KBService-compatible instance (FAISSService etc.).
            embedding_client: EmbeddingClient instance for query embedding.
        """
        self.kb_service = kb_service
        self.embedding_client = embedding_client

    async def search(self, query: str, top_k: int = 10, score_threshold: float = 0.0) -> list:
        """Embed the query and perform vector similarity search. Async."""
        if not query.strip():
            return []

        query_emb = await self.embedding_client.embed_query(query)
        results = self.kb_service.search(query_emb, top_k, score_threshold)

        logger.debug(f"Vector search: '{query[:50]}...' -> {len(results)} results")
        return results
