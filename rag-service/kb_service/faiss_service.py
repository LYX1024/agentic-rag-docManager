"""FAISS vector store implementation (adapted from LangChain-Chatchat)."""
import json
import os
from pathlib import Path
from typing import Optional
import numpy as np
import faiss
from loguru import logger

from .kb_service import KBService, register_kb_service


@register_kb_service("faiss")
class FAISSService(KBService):
    """FAISS-backed vector store with in-memory document index."""

    def __init__(self, kb_name: str, persist_dir: str):
        super().__init__(kb_name, persist_dir)
        self.index: Optional[faiss.Index] = None
        self.docstore: dict = {}  # doc_id -> {text, embedding, metadata}
        self._dimension: Optional[int] = None
        self._index_file = self.persist_dir / f"{kb_name}.faiss"
        self._docstore_file = self.persist_dir / f"{kb_name}.json"
        self.load()

    @property
    def _index_path(self):
        return str(self._index_file)

    @property
    def _docstore_path(self):
        return str(self._docstore_file)

    def do_init_index(self, dimension: int):
        """ 
        IndexFlatIP内积索引 -> 即余弦相似度
        进行归一化处理后，分数处理[-1, 1]

        索引类型选择
        IndexFlatIP：内积索引（当前使用）
        优点：配合归一化等价于余弦相似度
        缺点：暴力搜索，大数据量慢

        IndexFlatL2：欧氏距离索引
        优点：不需要归一化
        缺点：距离受向量模长影响

        IndexIVFFlat：倒排索引（加速搜索）
        优点：搜索更快
        缺点：需要训练，精度略低
        """
        self._dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product, use with normalized vectors
        self.docstore = {}

    def add_documents(self, texts: list, embeddings: list, metadatas: Optional[list] = None) -> list:
        """ 
        texts + embeddings + metadatas → FAISS + JSON docstore
        FAISS向量存储 + json持久化(原始文本块 + 向量数据块 + 元数据)
        """
        if not texts:
            return []

        embeddings = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(embeddings)  # L2归一化

        if self.index is None:
            self.do_init_index(embeddings.shape[1])

        start_idx = self.index.ntotal
        doc_ids = []
        for i, (text, emb) in enumerate(zip(texts, embeddings)):
            doc_id = f"{self.kb_name}_doc_{start_idx + i}"
            self.docstore[doc_id] = {
                "text": text,
                "embedding": emb.tolist() if isinstance(emb, np.ndarray) else emb,
                "metadata": metadatas[i] if metadatas else {}
            }
            doc_ids.append(doc_id)

        self.index.add(embeddings)
        self.save()
        logger.info(f"FAISS[{self.kb_name}]: added {len(texts)} docs, total={self.index.ntotal}")
        return doc_ids

    def search(self, query_embedding: list, top_k: int = 5, score_threshold: float = 0.0) -> list:
        """
        查询向量预处理 -> FAISS向量检索 -> 元数据回填
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        query = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query)

        scores, indices = self.index.search(query, min(top_k, self.index.ntotal))
        doc_ids = list(self.docstore.keys())

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(doc_ids):
                continue
            score_val = float(score)
            if score_val < score_threshold:
                continue
            doc_id = doc_ids[idx]
            doc = self.docstore.get(doc_id, {})
            results.append({
                "id": doc_id,
                "text": doc.get("text", ""),
                "score": score_val,
                "metadata": doc.get("metadata", {})
            })
        return results

    def delete_documents(self, doc_ids: list):
        for doc_id in doc_ids:
            self.docstore.pop(doc_id, None)
        self._rebuild_index()

    def get_document_count(self) -> int:
        return self.index.ntotal if self.index else 0

    def get_all_texts(self) -> list[dict]:
        return [{"id": k, "text": v["text"], "metadata": v.get("metadata", {})}
                for k, v in self.docstore.items()]

    def clear(self):
        self.index = None
        self.docstore = {}
        for f in [self._index_file, self._docstore_file]:
            if f.exists():
                f.unlink()
        logger.info(f"FAISS[{self.kb_name}]: cleared")

    def save(self):
        if self.index is not None:
            faiss.write_index(self.index, self._index_path)
        with open(self._docstore_path, "w", encoding="utf-8") as f:
            json.dump({"docstore": self.docstore, "dimension": self._dimension}, f, ensure_ascii=False)

    def load(self):
        if self._index_file.exists() and self._docstore_file.exists():
            try:
                self.index = faiss.read_index(self._index_path)
                with open(self._docstore_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.docstore = data.get("docstore", {})
                    self._dimension = data.get("dimension")
                logger.info(f"FAISS[{self.kb_name}]: loaded {self.index.ntotal} docs")
            except Exception as e:
                logger.warning(f"FAISS[{self.kb_name}]: failed to load, starting fresh: {e}")
                self.index = None
                self.docstore = {}
                self._dimension = None

    def _rebuild_index(self):
        if not self.docstore:
            self.index = None
            self.save()
            return
        dim = len(next(iter(self.docstore.values()))["embedding"])
        self.do_init_index(dim)
        embeddings = np.array([v["embedding"] for v in self.docstore.values()], dtype=np.float32)
        self.index.add(embeddings)
        self.save()
