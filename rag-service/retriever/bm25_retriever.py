"""BM25 retriever with jieba-based Chinese tokenization.

Uses a simplified TF-IDF / BM25 scoring implementation with jieba.lcut_for_search
for Chinese text segmentation. No external BM25 library required.
"""
import math
from typing import Optional
from collections import defaultdict
import jieba
from loguru import logger


class BM25Retriever:
    """BM25 retrieval with jieba tokenization for Chinese support.

    Rebuilds its corpus from kb_service.get_all_texts() on initialisation.
    后续考虑使用ES等专用关键词搜索数据库
    """

    def __init__(self, kb_service, k1: float = 1.5, b: float = 0.75):
        """Initialise the BM25 retriever.

        Args:
            kb_service: KBService-compatible instance (FAISSService etc.).
            k1: BM25 k1 parameter (term frequency saturation).
            b: BM25 b parameter (length normalisation).
        """
        self.kb_service = kb_service
        self.k1 = k1
        self.b = b
        self._corpus: list[list[str]] = []  # list of tokenised documents
        self._doc_entries: list[dict] = []  # parallel list of {id, text, metadata}
        self._avgdl: float = 0.0
        self._df: dict[str, int] = {}  # document frequency per term
        self._rebuild_index()

    def _rebuild_index(self):
        """Rebuild the BM25 index from the kb_service document store."""
        all_texts = self.kb_service.get_all_texts()

        self._corpus = []
        self._doc_entries = []
        self._df = defaultdict(int) #df：文档频率(词出现在了几篇文档中)

        for entry in all_texts:
            text = entry.get("text", "")
            tokens = jieba.lcut_for_search(text)    # 使用jieba进行中文分词，lcut_for_search粒度更细
            self._corpus.append(tokens)
            self._doc_entries.append({
                "id": entry.get("id", ""),
                "text": text,
                "metadata": entry.get("metadata", {}),
            })

            # Document frequency: count each unique term once per document
            unique_terms = set(tokens)
            for term in unique_terms:
                self._df[term] += 1 #对词去重

        # Average document length
        total_len = sum(len(tokens) for tokens in self._corpus)
        self._avgdl = total_len / len(self._corpus) if self._corpus else 0.0

        logger.info(
            f"BM25Retriever index rebuilt: {len(self._corpus)} docs, "
            f"avg_len={self._avgdl:.1f}, vocab_size={len(self._df)}"
        )

    def _idf(self, term: str) -> float:
        """
        IDF：Inverse Document Frequency，逆文档频率。用于衡量一个词“有多重要”
        Compute IDF for a term.
        """
        N = len(self._corpus)
        df = self._df.get(term, 0)
        if df == 0:
            return 0.0
        # Smooth IDF: log((N - df + 0.5) / (df + 0.5) + 1)
        # N = 文档总数;df = 包含词t的文档数;+0.5 = 平滑项;+1 = 保证正值
        return math.log((N - df + 0.5) / (df + 0.5) + 1.0)

    def _score(self, query_tokens: list[str], doc_idx: int) -> float:
        """
        Compute BM25 score for a query against a single document.
        BM25检索结果评分
        我也看不懂
        """
        doc_tokens = self._corpus[doc_idx]
        doc_len = len(doc_tokens)

        term_freqs = defaultdict(int)
        for t in doc_tokens:
            term_freqs[t] += 1

        score = 0.0
        for term in query_tokens:
            tf = term_freqs.get(term, 0)
            if tf == 0:
                continue
            idf = self._idf(term)
            numerator = tf * (self.k1 + 1.0)
            denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self._avgdl))
            score += idf * (numerator / denominator)

        return score

    def search(self, query: str, top_k: int = 10) -> list:
        """Search the corpus with BM25 scoring.

        Args:
            query: The search query string.
            top_k: Maximum number of results to return.

        Returns:
            List of dicts: [{id, text, score, metadata}, ...] sorted by score descending.
        
        查询分词 -> 计算全文档bm25分数 -> 排序并返回top_k结果
        """
        if not self._corpus:
            return []

        query_tokens = jieba.lcut_for_search(query)
        if not query_tokens:
            return []

        # Score every document
        scores = []
        for idx in range(len(self._corpus)):
            s = self._score(query_tokens, idx)
            if s > 0:
                scores.append((idx, s))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scores[:top_k]:
            entry = self._doc_entries[idx]
            results.append({
                "id": entry["id"],
                "text": entry["text"],
                "score": score,
                "metadata": entry["metadata"],
            })

        return results
