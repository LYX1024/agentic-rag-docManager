"""KBService abstract base class + factory (adapted from LangChain-Chatchat)."""
from abc import ABC, abstractmethod
from typing import Optional, Type, Dict
from pathlib import Path
from loguru import logger


class KBService(ABC):
    """Abstract base for all vector store backend implementations."""

    def __init__(self, kb_name: str, persist_dir: str):
        self.kb_name = kb_name
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def add_documents(self, texts: list, embeddings: list, metadatas: Optional[list] = None) -> list:
        """Add documents with embeddings to the vector store. Returns list of doc IDs."""

    @abstractmethod
    def search(self, query_embedding: list, top_k: int = 5, score_threshold: float = 0.0) -> list:
        """Vector similarity search. Returns list of {id, text, score, metadata}."""

    @abstractmethod
    def delete_documents(self, doc_ids: list):
        """Delete documents by their IDs."""

    @abstractmethod
    def get_document_count(self) -> int:
        """Return total document count in this store."""

    @abstractmethod
    def get_all_texts(self) -> list[dict]:
        """Return all texts with metadata. Needed for BM25 indexing."""

    @abstractmethod
    def clear(self):
        """Remove all documents and delete the store."""

    @abstractmethod
    def save(self):
        """Persist to disk."""

    @abstractmethod
    def load(self):
        """Load from disk."""


_kb_service_registry: Dict[str, Type[KBService]] = {}


def register_kb_service(vs_type: str):
    """Decorator to register a KBService implementation."""
    def decorator(cls: Type[KBService]):
        _kb_service_registry[vs_type.lower()] = cls
        logger.info(f"Registered KBService: {vs_type} -> {cls.__name__}")
        return cls
    return decorator


class KBServiceFactory:
    """Factory to get the appropriate KBService implementation."""

    @staticmethod
    def get_service(kb_name: str, vs_type: str, persist_dir: str) -> KBService:
        cls = _kb_service_registry.get(vs_type.lower())
        if cls is None:
            raise ValueError(f"Unknown vs_type: {vs_type}. Registered: {list(_kb_service_registry.keys())}")
        return cls(kb_name, persist_dir)

    @staticmethod
    def list_types() -> list:
        return list(_kb_service_registry.keys())
