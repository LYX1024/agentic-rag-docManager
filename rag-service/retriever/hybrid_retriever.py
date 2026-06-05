"""Hybrid retriever combining BM25 + Vector search via Reciprocal Rank Fusion (RRF)."""
from loguru import logger
from .bm25_retriever import BM25Retriever
from .vector_retriever import VectorRetriever


class HybridRetriever:
    """Hybrid retrieval fusing BM25 (lexical) and vector (semantic) search with RRF.

    Reciprocal Rank Fusion (RRF) combines ranked result lists from multiple
    retrieval methods into a single ranked list.

    RRF formula:
        score(d) = sum over retrievers i of (weight_i / (k + rank_i))
    where:
        - k is a constant (default 60) to prevent very high ranks from dominating
        - weight_i is the contribution weight for retriever i
    """

    def __init__(
        self,
        kb_service,
        embedding_client,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7,
        rrf_k: int = 60,
    ):
        """Initialize the hybrid retriever.

        Args:
            kb_service: KBService-compatible instance.
            embedding_client: EmbeddingClient for query embedding.
            bm25_weight: Weight for BM25 results in RRF fusion.
            vector_weight: Weight for vector results in RRF fusion.
            rrf_k: RRF constant to dampen rank effect.
        """
        self.bm25 = BM25Retriever(kb_service)
        self.vector = VectorRetriever(kb_service, embedding_client)
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.rrf_k = rrf_k

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> list:
        """Retrieve and fuse results from both BM25 and vector search.

        Args:
            query: The search query string.
            top_k: Number of final results to return.
            score_threshold: Minimum RRF score threshold.

        Returns:
            List of dicts: [{id, text, score, metadata}, ...] sorted by score desc.
        """
        # Get 2x results from each retriever for better recall
        fetch_k = top_k * 2

        bm25_results = self.bm25.search(query, top_k=fetch_k)
        vector_results = self.vector.search(query, top_k=fetch_k, score_threshold=0.0)

        logger.debug(
            f"Hybrid pre-fusion: BM25={len(bm25_results)}, Vector={len(vector_results)}"
        )

        # Fuse via RRF
        fused = self._rrf_fusion(
            bm25_results, vector_results,
            weight_a=self.bm25_weight, weight_b=self.vector_weight
        )

        # Filter by threshold
        if score_threshold > 0:
            fused = [r for r in fused if r["score"] >= score_threshold]

        # Sort by fused score descending and take top_k
        fused.sort(key=lambda x: x["score"], reverse=True)
        fused = fused[:top_k]

        logger.info(
            f"HybridR: query='{query[:60]}...' -> "
            f"BM25={len(bm25_results)} + Vec={len(vector_results)} "
            f"= fused={len(fused)}"
        )
        return fused

    def _rrf_fusion(
        self,
        results_a: list[dict],
        results_b: list[dict],
        weight_a: float,
        weight_b: float,
    ) -> list[dict]:
        """Fuse two ranked result lists with RRF.

        Args:
            results_a: First ranked list (e.g., BM25).
            results_b: Second ranked list (e.g., vector).
            weight_a: Weight for results_a.
            weight_b: Weight for results_b.

        Returns:
            Fused list of dicts with RRF scores.
        """
        fused_map: dict[str, dict] = {}

        # Process first list
        for rank, item in enumerate(results_a):
            doc_id = item["id"]
            rrf_score = weight_a / (self.rrf_k + rank + 1)
            if doc_id in fused_map:
                fused_map[doc_id]["score"] += rrf_score
            else:
                fused_map[doc_id] = {
                    "id": doc_id,
                    "text": item["text"],
                    "score": rrf_score,
                    "metadata": item.get("metadata", {}),
                }

        # Process second list
        for rank, item in enumerate(results_b):
            doc_id = item["id"]
            rrf_score = weight_b / (self.rrf_k + rank + 1)
            if doc_id in fused_map:
                fused_map[doc_id]["score"] += rrf_score
            else:
                fused_map[doc_id] = {
                    "id": doc_id,
                    "text": item["text"],
                    "score": rrf_score,
                    "metadata": item.get("metadata", {}),
                }

        return list(fused_map.values())

    def rebuild_bm25(self):
        """Rebuild the BM25 index (call after document changes)."""
        self.bm25._rebuild_index()
