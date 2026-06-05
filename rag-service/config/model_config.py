"""Pydantic-based YAML configuration model (adapted from LangChain-Chatchat)."""
import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env from project root (2 levels up from rag-service/config/)
CONFIG_DIR = Path(__file__).parent
PROJECT_ROOT = CONFIG_DIR.parent.parent
load_dotenv(PROJECT_ROOT / ".env")
DEFAULT_CONFIG = CONFIG_DIR / "config.yaml"


class EmbeddingConfig(BaseModel):
    api_base: str = os.getenv("EMBEDDING_API_BASE", "https://api.openai.com/v1")
    api_key: str = os.getenv("EMBEDDING_API_KEY", "")
    model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    dimension: int = 1536


class VectorStoreConfig(BaseModel):
    type: str = "faiss"  # faiss | milvus | chroma
    persist_directory: str = "/data/faiss"


class TextSplitterConfig(BaseModel):
    chunk_size: int = 250
    chunk_overlap: int = 50
    separators: list = ["\n\n", "\n", "。", "！", "？", "，", " ", ""]


class RetrieverConfig(BaseModel):
    bm25_weight: float = 0.3
    vector_weight: float = 0.7
    top_k: int = 5
    score_threshold: float = 0.35
    rrf_k: int = 60


class RerankerConfig(BaseModel):
    model_name: str = "BAAI/bge-reranker-large"
    top_n: int = 3
    enabled: bool = True


class OCRConfig(BaseModel):
    use_rapid_ocr: bool = True
    ocr_lang: str = "ch"


class StorageConfig(BaseModel):
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
    bucket: str = "knowledge-base"
    temp_dir: str = "/tmp/rag-service"


class LLMConfig(BaseModel):
    api_base: str = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
    api_key: str = os.getenv("LLM_API_KEY", "")
    model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    temperature: float = 0.7


class AppConfig(BaseModel):
    embedding: EmbeddingConfig = EmbeddingConfig()
    vector_store: VectorStoreConfig = VectorStoreConfig()
    text_splitter: TextSplitterConfig = TextSplitterConfig()
    retriever: RetrieverConfig = RetrieverConfig()
    reranker: RerankerConfig = RerankerConfig()
    ocr: OCRConfig = OCRConfig()
    storage: StorageConfig = StorageConfig()
    llm: LLMConfig = LLMConfig()
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    path = config_path or DEFAULT_CONFIG
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    config = AppConfig(
        embedding=EmbeddingConfig(**data.get("embedding", {})),
        vector_store=VectorStoreConfig(**data.get("vector_store", {})),
        text_splitter=TextSplitterConfig(**data.get("text_splitter", {})),
        retriever=RetrieverConfig(**data.get("retriever", {})),
        reranker=RerankerConfig(**data.get("reranker", {})),
        ocr=OCRConfig(**data.get("ocr", {})),
        storage=StorageConfig(**data.get("storage", {})),
        llm=LLMConfig(**data.get("llm", {})),
    )
    return config
