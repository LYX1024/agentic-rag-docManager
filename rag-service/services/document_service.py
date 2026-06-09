"""gRPC DocumentService implementation."""
import asyncio
import json
import uuid
from pathlib import Path
from datetime import datetime

import grpc
import redis
from loguru import logger

from config.model_config import AppConfig
from embedding.embed_model import EmbeddingClient
from storage.minio_client import MinIOClient
from kb_service.kb_service import KBServiceFactory
from pipeline.ingestion import ingest_document

from generated import document_pb2
from generated import document_pb2_grpc
from generated import common_pb2


# In-memory document status tracker (per process)
_doc_status_store: dict[str, dict] = {}


class DocumentServicer(document_pb2_grpc.DocumentServiceServicer):
    """Manages document lifecycle: upload, list, delete, reprocess, status."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.persist_dir = Path(config.vector_store.persist_directory)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._minio_client: MinIOClient | None = None
        self._embedding_client: EmbeddingClient | None = None
        logger.info("DocumentServicer initialized")

    @property
    def minio_client(self) -> MinIOClient:
        if self._minio_client is None:
            self._minio_client = MinIOClient(
                endpoint=self.config.storage.minio_endpoint,
                access_key=self.config.storage.access_key,
                secret_key=self.config.storage.secret_key,
                bucket=self.config.storage.bucket,
                temp_dir=self.config.storage.temp_dir,
            )
        return self._minio_client

    @property
    def embedding_client(self) -> EmbeddingClient:
        if self._embedding_client is None:
            self._embedding_client = EmbeddingClient(
                base_url=self.config.embedding.api_base,
                api_key=self.config.embedding.api_key,
                model=self.config.embedding.model,
                dimension=self.config.embedding.dimension,
            )
        return self._embedding_client

    def _get_kb_name(self, kb_id: int) -> str:
        """Resolve kb_id to kb_name via the registry."""
        from services.kb_management_service import KBManagementServicer
        # Use registry file directly
        registry_path = self.persist_dir / "_kb_registry.json"
        if registry_path.exists():
            import json
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
            for _, entry in registry.items():
                if entry.get("id") == kb_id:
                    return entry["name"]
        return f"kb_{kb_id}"

    async def UploadDocument(self, request, context):
        """Accept document upload and trigger async ingestion.

        The file is already stored in MinIO by the Java client. This endpoint
        returns immediately and processes embedding in the background.
        """
        try:
            kb_name = self._get_kb_name(request.kb_id)
            file_name = request.file_name
            file_ext = request.file_ext
            minio_key = request.minio_key

            logger.info(
                f"UploadDocument: kb={kb_name}, file={file_name}, minio_key={minio_key}"
            )

            # Dedup: skip if already being processed
            if minio_key in _doc_status_store:
                logger.warning(f"Document already being processed: {minio_key}")
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                context.set_details(f"Document {file_name} is already being processed")
                return document_pb2.DocumentInfo()

            # Track active ingestion (keyed by minio_key for dedup)
            _doc_status_store[minio_key] = common_pb2.PARSING

            # Submit async ingestion task
            asyncio.create_task(
                self._run_ingestion(minio_key, kb_name, file_name, file_ext))

            now = datetime.now().isoformat()
            return document_pb2.DocumentInfo(
                id=hash(minio_key) & 0x7FFFFFFFFFFFFFFF,
                kb_id=request.kb_id,
                file_name=file_name,
                file_ext=file_ext,
                file_size=request.file_size,
                minio_key=minio_key,
                file_version=1,
                status=common_pb2.PARSING,
                chunk_count=0,
                error_msg="",
                created_at=now,
                updated_at=now,
            )

        except Exception as e:
            logger.error(f"UploadDocument failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return document_pb2.DocumentInfo()

    async def _run_ingestion(self, minio_key: str, kb_name: str,
                              file_name: str, file_ext: str):
        """Run ingestion as async background task."""
        result = await ingest_document(
            minio_key=minio_key,
            kb_name=kb_name,
            file_name=file_name,
            file_ext=file_ext,
            config=self.config,
            minio_client=self.minio_client,
            embedding_client=self.embedding_client,
        )

        if result.success:
            logger.info(f"Ingestion complete: {file_name} -> {result.chunk_count} chunks")
        else:
            logger.error(f"Ingestion failed: {file_name}: {result.error_msg}")

        # Clean up in-memory tracker and notify Java
        _doc_status_store.pop(minio_key, None)
        self._notify_java(minio_key, result)

    def _notify_java(self, minio_key: str, result):
        """Notify Java backend of ingestion result via Redis Pub/Sub."""
        try:
            r = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                password=self.config.redis_password,
                decode_responses=True,
            )
            payload = json.dumps({
                "minio_key": minio_key,
                "status": "COMPLETED" if result.success else "FAILED",
                "chunk_count": result.chunk_count,
                "error_msg": result.error_msg or "",
            })
            r.publish("ingestion:status", payload)
            logger.debug(f"Published to Redis: {minio_key} -> {payload}")
        except Exception as e:
            logger.warning(f"Failed to publish to Redis: {e}")

    async def ListDocuments(self, request, context):
        """List documents in a knowledge base."""
        try:
            kb_name = self._get_kb_name(request.kb_id)

            # Get all documents from the vector store
            try:
                kb_svc = KBServiceFactory.get_service(
                    kb_name=kb_name,
                    vs_type=self.config.vector_store.type,
                    persist_dir=str(self.persist_dir),
                )
                all_texts = kb_svc.get_all_texts()
            except Exception:
                all_texts = []

            # Aggregate by minio_key / source_file
            file_map: dict[str, dict] = {}
            for doc in all_texts:
                meta = doc.get("metadata", {})
                source = meta.get("source_file", "unknown")
                if source not in file_map:
                    file_map[source] = {
                        "file_name": source,
                        "file_ext": meta.get("source_ext", ""),
                        "minio_key": meta.get("minio_key", ""),
                        "chunk_count": 0,
                        "status": common_pb2.COMPLETED,
                    }
                file_map[source]["chunk_count"] += 1

            documents = []
            for i, (fname, info) in enumerate(file_map.items()):
                documents.append(document_pb2.DocumentInfo(
                    id=i + 1,
                    kb_id=request.kb_id,
                    file_name=info["file_name"],
                    file_ext=info["file_ext"],
                    file_size=0,
                    minio_key=info["minio_key"],
                    file_version=1,
                    status=info.get("status", common_pb2.COMPLETED),
                    chunk_count=info["chunk_count"],
                    error_msg="",
                    created_at="",
                    updated_at="",
                ))

            page = request.page.page if request.page and request.page.page > 0 else 1
            page_size = request.page.page_size if request.page and request.page.page_size > 0 else 20
            total = len(documents)
            start = (page - 1) * page_size
            end = start + page_size

            page_info = common_pb2.PageInfo(total=total, page=page, page_size=page_size)

            return document_pb2.ListDocsResponse(
                documents=documents[start:end],
                page=page_info,
            )

        except Exception as e:
            logger.error(f"ListDocuments failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return document_pb2.ListDocsResponse()

    async def DeleteDocument(self, request, context):
        """Delete a document and its chunks from the knowledge base."""
        try:
            kb_name = self._get_kb_name(request.kb_id)
            minio_key = request.minio_key

            logger.info(f"DeleteDocument: kb={kb_name}, minio_key={minio_key}")

            try:
                kb_svc = KBServiceFactory.get_service(
                    kb_name=kb_name,
                    vs_type=self.config.vector_store.type,
                    persist_dir=str(self.persist_dir),
                )
                all_texts = kb_svc.get_all_texts()

                # Find doc_ids that match this minio_key
                ids_to_delete = []
                for doc in all_texts:
                    meta = doc.get("metadata", {})
                    if meta.get("minio_key") == minio_key:
                        ids_to_delete.append(doc["id"])

                if ids_to_delete:
                    kb_svc.delete_documents(ids_to_delete)
                    logger.info(f"Deleted {len(ids_to_delete)} chunks for {minio_key}")
            except Exception as ex:
                logger.warning(f"Error cleaning chunks for {minio_key}: {ex}")

            # Also delete from MinIO
            try:
                self.minio_client.delete_file(minio_key)
            except Exception as ex:
                logger.warning(f"Error deleting MinIO object {minio_key}: {ex}")

            _doc_status_store.pop(minio_key, None)

            return common_pb2.StatusResponse(
                success=True,
                message=f"Document '{minio_key}' deleted successfully",
            )

        except Exception as e:
            logger.error(f"DeleteDocument failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.StatusResponse(success=False, message=str(e))

    async def ReprocessDocument(self, request, context):
        """Re-ingest a document (delete old chunks + re-process)."""
        try:
            kb_name = self._get_kb_name(request.kb_id)
            minio_key = request.minio_key

            logger.info(f"ReprocessDocument: kb={kb_name}, minio_key={minio_key}")

            # Step 1: Delete old chunks
            try:
                kb_svc = KBServiceFactory.get_service(
                    kb_name=kb_name,
                    vs_type=self.config.vector_store.type,
                    persist_dir=str(self.persist_dir),
                )
                all_texts = kb_svc.get_all_texts()
                ids_to_delete = [
                    doc["id"] for doc in all_texts
                    if doc.get("metadata", {}).get("minio_key") == minio_key
                ]
                if ids_to_delete:
                    kb_svc.delete_documents(ids_to_delete)
                    logger.info(f"Removed {len(ids_to_delete)} old chunks for reprocessing")
            except Exception as ex:
                logger.warning(f"Error cleaning old chunks during reprocess: {ex}")

            # Step 2: Re-ingest
            file_name = Path(minio_key).name
            file_ext = Path(file_name).suffix

            result = ingest_document(
                minio_key=minio_key,
                kb_name=kb_name,
                file_name=file_name,
                file_ext=file_ext,
                config=self.config,
                minio_client=self.minio_client,
                embedding_client=self.embedding_client,
            )

            if result.success:
                return common_pb2.StatusResponse(
                    success=True,
                    message=f"Document reprocessed: {result.chunk_count} chunks",
                )
            else:
                return common_pb2.StatusResponse(
                    success=False,
                    message=f"Reprocessing failed: {result.error_msg}",
                )

        except Exception as e:
            logger.error(f"ReprocessDocument failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.StatusResponse(success=False, message=str(e))

    async def GetDocumentStatus(self, request, context):
        """Get processing status. PARSING if in active tracker, otherwise COMPLETED."""
        try:
            # Check if minio_key is in active ingestion
            minio_key = request.minio_key if hasattr(request, 'minio_key') else ""
            if minio_key and minio_key in _doc_status_store:
                return document_pb2.DocStatusResponse(
                    file_id=request.file_id, status=common_pb2.PARSING,
                    chunk_count=0, error_msg="")

            return document_pb2.DocStatusResponse(
                file_id=request.file_id, status=common_pb2.COMPLETED,
                chunk_count=0, error_msg="")

        except Exception as e:
            logger.error(f"GetDocumentStatus failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return document_pb2.DocStatusResponse()

    async def BatchUploadDocuments(self, request, context):
        """Upload multiple documents in a batch."""
        try:
            responses = []
            success_count = 0
            fail_count = 0

            for doc_req in request.documents:
                try:
                    # Reuse UploadDocument logic
                    single_request = document_pb2.UploadDocRequest(
                        kb_id=doc_req.kb_id,
                        file_name=doc_req.file_name,
                        file_ext=doc_req.file_ext,
                        minio_key=doc_req.minio_key,
                        file_size=doc_req.file_size,
                    )
                    # Create a dummy context for each sub-call
                    result = self.UploadDocument(single_request, context)
                    responses.append(result)
                    if result.status == common_pb2.COMPLETED:
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as ex:
                    logger.error(f"Batch upload item failed: {doc_req.file_name}: {ex}")
                    fail_count += 1

            return document_pb2.BatchUploadDocsResponse(
                documents=responses,
                success_count=success_count,
                fail_count=fail_count,
            )

        except Exception as e:
            logger.error(f"BatchUploadDocuments failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return document_pb2.BatchUploadDocsResponse()
