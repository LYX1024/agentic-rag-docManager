"""Async gRPC ChatService implementation with RAG streaming chat."""
import asyncio
import uuid
from pathlib import Path
from datetime import datetime

import grpc
from loguru import logger

from config.model_config import AppConfig
from embedding.embed_model import EmbeddingClient
from kb_service.kb_service import KBServiceFactory
from retriever.hybrid_retriever import HybridRetriever
from services.chat.llm_client import LLMClient
from services.chat.history import ChatHistoryManager
from services.chat.agentic_rag import agentic_rag_stream

from generated import chat_pb2
from generated import chat_pb2_grpc
from generated import common_pb2


class ChatServicer(chat_pb2_grpc.ChatServiceServicer):

    def __init__(self, config: AppConfig):
        self.config = config
        self.persist_dir = Path(config.vector_store.persist_directory)
        self._embedding_client: EmbeddingClient | None = None
        self._retrievers: dict[str, HybridRetriever] = {}
        self._llm_client: LLMClient | None = None
        self._history = ChatHistoryManager(
            llm_api_base=config.llm.api_base,
            llm_api_key=config.llm.api_key,
            llm_model=config.llm.model,
        )
        logger.info("ChatServicer initialized")

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

    @property
    def llm_client(self) -> LLMClient:
        if self._llm_client is None:
            self._llm_client = LLMClient(
                base_url=self.config.llm.api_base,
                api_key=self.config.llm.api_key,
            )
        return self._llm_client

    def _get_kb_name(self, kb_id: int) -> str:
        registry_path = self.persist_dir / "_kb_registry.json"
        if registry_path.exists():
            import json
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
            for _, entry in registry.items():
                if entry.get("id") == kb_id:
                    return entry["name"]
        return f"kb_{kb_id}"

    async def RagChat(self, request, context):
        try:
            query = request.query
            kb_name = request.kb_name if request.kb_name else self._get_kb_name(request.kb_id)
            top_k = request.top_k or self.config.retriever.top_k
            score_threshold = request.score_threshold or self.config.retriever.score_threshold
            session_id = request.session_id or str(uuid.uuid4())
            llm_model = request.llm_model or self.config.llm.model
            temperature = request.temperature or self.config.llm.temperature

            if not query:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Query is required")

            logger.info(f"RagChat: session={session_id}, query='{query[:60]}...'")

            # Get or create retriever
            kb_svc = KBServiceFactory.get_service(
                kb_name=kb_name, vs_type=self.config.vector_store.type,
                persist_dir=str(self.persist_dir))
            if kb_name not in self._retrievers:
                self._retrievers[kb_name] = HybridRetriever(
                    kb_service=kb_svc, embedding_client=self.embedding_client,
                    bm25_weight=self.config.retriever.bm25_weight,
                    vector_weight=self.config.retriever.vector_weight,
                    rrf_k=self.config.retriever.rrf_k)
            retriever = self._retrievers[kb_name]

            # Agentic RAG: ReAct loop with search function calling
            message_id = str(uuid.uuid4())
            full_response = ""
            source_docs = []
            async for event_type, data in agentic_rag_stream(
                    query=query, retriever=retriever,
                    llm_client=self.llm_client, llm_model=llm_model,
                    temperature=temperature):
                if event_type == "thinking":
                    await context.write(chat_pb2.RagChatChunk(
                        token=f"[{data}] ", finished=False, sources=[],
                        message_id=message_id, session_id=session_id))
                elif event_type == "sources":
                    source_docs = data
                elif event_type == "answer":
                    full_response = data
                    await context.write(chat_pb2.RagChatChunk(
                        token=data, finished=False, sources=[],
                        message_id=message_id, session_id=session_id))

            # Save history
            self._history.add_turn(session_id, query, full_response,
                                    [{"file_name": s.file_name, "file_ext": s.file_ext,
                                      "chunk_text": s.chunk_text, "chunk_index": s.chunk_index,
                                      "score": s.score} for s in source_docs])
            asyncio.create_task(self._history.maybe_summarize(session_id))

            # Final chunk
            await context.write(chat_pb2.RagChatChunk(
                token="", finished=True, sources=source_docs,
                message_id=message_id, session_id=session_id))

            logger.info(f"RagChat complete: session={session_id}, "
                        f"response_len={len(full_response)}, sources={len(source_docs)}")

        except Exception as e:
            logger.error(f"RagChat failed: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def GetChatHistory(self, request, context):
        try:
            turns = self._history.get_raw(request.session_id)
            limit = request.limit or 50
            turns = turns[-limit:]

            records = []
            for t in turns:
                sources = [common_pb2.SourceDoc(
                    file_name=s.get("file_name", ""), file_ext=s.get("file_ext", ""),
                    chunk_text=s.get("chunk_text", ""), chunk_index=s.get("chunk_index", 0),
                    score=s.get("score", 0.0)) for s in (t.get("sources") or [])]
                records.append(chat_pb2.ChatHistoryRecord(
                    id=t.get("id", ""), role=t.get("role", ""),
                    content=t.get("content", ""), sources=sources,
                    created_at=t.get("created_at", "")))

            return chat_pb2.GetChatHistoryResponse(
                messages=records, session_id=request.session_id, title="")

        except Exception as e:
            logger.error(f"GetChatHistory failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return chat_pb2.GetChatHistoryResponse()

    async def DeleteChatSession(self, request, context):
        try:
            self._history.clear_session(request.session_id)
            logger.info(f"Chat session deleted: {request.session_id}")
            return common_pb2.StatusResponse(
                success=True, message=f"Session '{request.session_id}' deleted")
        except Exception as e:
            logger.error(f"DeleteChatSession failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.StatusResponse(success=False, message=str(e))
