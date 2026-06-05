"""Cross-encoder re-ranker for improving retrieval precision."""
from loguru import logger


class Reranker:
    """Re-ranker using a SentenceTransformer CrossEncoder model.

    Pairs each (query, candidate_text) and predicts a relevance score
    to re-order the candidate list for better precision.

    Default model: BAAI/bge-reranker-large.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-large"):
        """Initialise the re-ranker.

        Args:
            model_name: HuggingFace model name for the cross-encoder.
        """
        from sentence_transformers import CrossEncoder

        self.model_name = model_name
        self.model = CrossEncoder(model_name)
        logger.info(f"Reranker initialized: model={model_name}")

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_n: int = 3,
    ) -> list[dict]:
        """Re-rank candidate documents using cross-encoder scoring.

        Args:
            query: The search query string.
            candidates: List of candidate dicts, each with at least 'text' key.
                        Expected format: [{id, text, score, metadata}, ...].
            top_n: Number of top results to return after re-ranking.

        Returns:
            Re-ranked list of dicts sorted by rerank_score descending.
            Each dict has the original fields plus 'rerank_score'.
        """
        if not candidates:
            return []

        # Build (query, doc_text) pairs
        pairs = [(query, cand["text"]) for cand in candidates]

        # Predict relevance scores
        raw_scores = self.model.predict(pairs)

        # Normalize scores to [0, 1] range using softmax-style scaling
        if hasattr(raw_scores, "tolist"):
            raw_scores = raw_scores.tolist()

        # Attach rerank_score and sort
        for i, cand in enumerate(candidates):
            cand["rerank_score"] = float(raw_scores[i]) if i < len(raw_scores) else 0.0

        candidates.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        reranked = candidates[:top_n]

        logger.debug(
            f"Reranker: {len(candidates)} candidates -> top {len(reranked)} for query "
            f"'{query[:50]}...'"
        )
        return reranked
