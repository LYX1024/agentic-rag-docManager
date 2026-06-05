"""Full document ingestion pipeline: download -> parse -> chunk -> embed -> store."""
import hashlib
from pathlib import Path
from typing import Optional
from loguru import logger

from config.model_config import AppConfig
from storage.minio_client import MinIOClient
from embedding.embed_model import EmbeddingClient
from kb_service.kb_service import KBServiceFactory
from loader.loader_dict import LOADER_DICT
from splitter.chinese_recursive_splitter import ChineseRecursiveTextSplitter
from splitter.zh_title_enhance import zh_title_enhance


class IngestionResult:
    def __init__(self, success: bool, chunk_count: int, doc_ids: list, error_msg: Optional[str] = None):
        self.success = success
        self.chunk_count = chunk_count
        self.doc_ids = doc_ids
        self.error_msg = error_msg


def ingest_document(
    minio_key: str,
    kb_name: str,
    file_name: str,
    file_ext: str,
    config: AppConfig,
    minio_client: Optional[MinIOClient] = None,
    embedding_client: Optional[EmbeddingClient] = None,
) -> IngestionResult:
    """
    Full ingestion pipeline for a single document.

    Steps:
    1. Download file from MinIO to temp dir
    2. Load document using appropriate loader (based on file extension)
    3. Split into chunks using ChineseRecursiveTextSplitter
    4. Enhance chunks with title hierarchy (zh_title_enhance)
    5. Embed chunks using OpenAI-compatible API
    6. Store embeddings in FAISS via KBService

    Args:
        minio_key: MinIO object key
        kb_name: Knowledge base name
        file_name: Original file name
        file_ext: File extension (with dot, e.g. ".pdf")
        config: Application configuration
        minio_client: Optional pre-configured MinIO client
        embedding_client: Optional pre-configured embedding client

    Returns:
        IngestionResult with success status, chunk count, and doc IDs
    """
    if minio_client is None:
        minio_client = MinIOClient(
            endpoint=config.storage.minio_endpoint,
            access_key=config.storage.access_key,
            secret_key=config.storage.secret_key,
            bucket=config.storage.bucket,
            temp_dir=config.storage.temp_dir,
        )

    if embedding_client is None:
        embedding_client = EmbeddingClient(
            base_url=config.embedding.api_base,
            api_key=config.embedding.api_key,
            model=config.embedding.model,
            dimension=config.embedding.dimension,
        )

    local_path = None
    try:
        # Step 1: Download from MinIO
        local_path = Path(config.storage.temp_dir) / kb_name / file_name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        minio_client.download_file(minio_key, str(local_path))
        logger.info(f"[{kb_name}] Downloaded: {minio_key} -> {local_path}")

        # Step 2: Load document
        loader = LOADER_DICT.get(file_ext.lower())
        if loader is None:
            raise ValueError(f"Unsupported file type: {file_ext}")

        documents = loader(str(local_path))
        if not documents:
            raise ValueError("Document loaded but produced no content")
        logger.info(f"[{kb_name}] Loaded {len(documents)} document(s) from {file_name}")

        # Step 3: Split into chunks
        splitter = ChineseRecursiveTextSplitter(
            chunk_size=config.text_splitter.chunk_size,
            chunk_overlap=config.text_splitter.chunk_overlap,
            separators=config.text_splitter.separators,
        )
        chunks = splitter.split_documents(documents)
        logger.info(f"[{kb_name}] Split into {len(chunks)} chunks")

        # Step 4: Title enhance (prepend hierarchy to each chunk)
        if chunks:
            chunks = zh_title_enhance(chunks)

        # Step 5: Build texts and metadatas
        texts = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            text = chunk.page_content if hasattr(chunk, "page_content") else str(chunk)
            texts.append(text)
            chunk_hash = hashlib.sha256(text.encode()).hexdigest()
            metadatas.append({
                "source_file": file_name,
                "source_ext": file_ext,
                "minio_key": minio_key,
                "chunk_index": i,
                "chunk_hash": chunk_hash,
                **(chunk.metadata if hasattr(chunk, "metadata") and chunk.metadata else {}),
            })

        # Step 6: Embed
        embeddings = embedding_client.embed_documents(texts)
        logger.info(f"[{kb_name}] Embedded {len(embeddings)} chunks, dim={len(embeddings[0]) if embeddings else 0}")

        # Step 7: Store in FAISS
        kb_service = KBServiceFactory.get_service(
            kb_name=kb_name,
            vs_type=config.vector_store.type,
            persist_dir=config.vector_store.persist_directory,
        )
        doc_ids = kb_service.add_documents(texts, embeddings, metadatas)
        logger.info(f"[{kb_name}] Stored {len(doc_ids)} docs in FAISS")

        return IngestionResult(
            success=True,
            chunk_count=len(chunks),
            doc_ids=doc_ids,
        )

    except Exception as e:
        logger.error(f"[{kb_name}] Ingestion failed for {file_name}: {e}")
        return IngestionResult(
            success=False,
            chunk_count=0,
            doc_ids=[],
            error_msg=str(e),
        )
    finally:
        if local_path is not None:
            local_path.unlink(missing_ok=True)
