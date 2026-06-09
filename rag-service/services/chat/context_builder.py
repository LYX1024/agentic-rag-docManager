"""Build prompt context from retrieved chunks."""
from generated import common_pb2


def build_context_and_sources(retrieved: list) -> tuple[str, list]:
    """Build context text and SourceDoc list from retrieval results.

    Args:
        retrieved: list of dicts with keys {id, text, score, metadata}

    Returns:
        (context_text, source_docs) where context_text is concatenated chunks
        and source_docs is a list of common_pb2.SourceDoc proto messages.
    """
    chunks_texts = []
    source_docs = []

    for i, chunk in enumerate(retrieved):
        chunks_texts.append(f"[{i + 1}] {chunk['text']}")
        meta = chunk.get("metadata", {})
        source_docs.append(common_pb2.SourceDoc(
            file_name=meta.get("source_file", ""),
            file_ext=meta.get("source_ext", ""),
            chunk_text=chunk.get("text", ""),
            chunk_index=meta.get("chunk_index", 0),
            score=float(chunk.get("rerank_score", chunk.get("score", 0.0))),
        ))

    context_text = "\n\n".join(chunks_texts) if chunks_texts else "暂无相关参考资料。"
    return context_text, source_docs
