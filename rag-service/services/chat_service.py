"""Async gRPC ChatService implementation with RAG streaming chat."""
import asyncio
import uuid
import time as time_mod
from pathlib import Path
from datetime import datetime

import grpc
from openai import AsyncOpenAI
from loguru import logger

from config.model_config import AppConfig
from embedding.embed_model import EmbeddingClient
from kb_service.kb_service import KBServiceFactory
from retriever.hybrid_retriever import HybridRetriever
from retriever.reranker import Reranker

from generated import chat_pb2
from generated import chat_pb2_grpc
from generated import common_pb2


RAG_PROMPT_TEMPLATE = (
    "你是一个知识库助手。请基于以下参考资料回答用户的问题。"
    "如果参考资料中没有相关信息，请如实告知。\n\n"
    "参考资料：\n"
    "{context}\n\n"
    "用户问题：{query}"
)

_chat_sessions: dict[str, dict] = {}
_chat_histories: dict[str, list[dict]] = {}


class ChatServicer(chat_pb2_grpc.ChatServiceServicer):

    def __init__(self, config: AppConfig):
        self.config = config
        self.persist_dir = Path(config.vector_store.persist_directory)
        self._embedding_client: EmbeddingClient | None = None
        self._retrievers: dict[str, HybridRetriever] = {}
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

    def _build_prompt(self, query: str, context_text: str) -> str:
        return RAG_PROMPT_TEMPLATE.format(context=context_text, query=query)

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

            message_id = str(uuid.uuid4())
            logger.info(f"RagChat: session={session_id}, query='{query[:60]}...'")

            # Step 1: Retrieve (CPU-bound, run in thread)
            kb_svc = KBServiceFactory.get_service(
                kb_name=kb_name, vs_type=self.config.vector_store.type, persist_dir=str(self.persist_dir))
            retriever = HybridRetriever(
                kb_service=kb_svc, embedding_client=self.embedding_client,
                bm25_weight=self.config.retriever.bm25_weight, vector_weight=self.config.retriever.vector_weight,
                rrf_k=self.config.retriever.rrf_k)
            retrieved = await asyncio.to_thread(
                retriever.retrieve, query=query, top_k=top_k, score_threshold=score_threshold)

            # Step 2: Build context
            chunks_texts = [f"[{i + 1}] {chunk['text']}" for i, chunk in enumerate(retrieved)]
            context_text = "\n\n".join(chunks_texts) if chunks_texts else "暂无相关参考资料。"
            prompt = self._build_prompt(query=query, context_text=context_text)

            # Step 3: Build messages with history
            messages = []
            history = _chat_histories.get(session_id, [])
            for h in history:
                messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": prompt})

            # Step 4: Build source docs
            source_docs = []
            for chunk in retrieved:
                meta = chunk.get("metadata", {})
                source_docs.append(common_pb2.SourceDoc(
                    file_name=meta.get("source_file", ""),
                    file_ext=meta.get("source_ext", ""),
                    chunk_text=chunk.get("text", ""),
                    chunk_index=meta.get("chunk_index", 0),
                    score=float(chunk.get("rerank_score", chunk.get("score", 0.0))),
                ))

            # Step 5: Async LLM streaming
            full_response = ""
            try:
                llm_client = AsyncOpenAI(
                    base_url=self.config.llm.api_base,
                    api_key=self.config.llm.api_key,
                    timeout=120.0,
                )

                stream = await llm_client.chat.completions.create(
                    model=llm_model, messages=messages, temperature=temperature, stream=True)

                async for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            token = delta.content
                            full_response += token
                            await context.write(chat_pb2.RagChatChunk(
                                token=token, finished=False, sources=[],
                                message_id=message_id, session_id=session_id))

            except Exception as llm_err:
                logger.error(f"LLM streaming failed: {llm_err}")
                error_msg = f"[错误] 大模型调用失败: {str(llm_err)}"
                await context.write(chat_pb2.RagChatChunk(
                    token=error_msg, finished=True, sources=source_docs,
                    message_id=message_id, session_id=session_id))
                return

            # Step 6: Save chat history
            if session_id not in _chat_histories:
                _chat_histories[session_id] = []
            _chat_histories[session_id].append({
                "id": message_id, "role": "user", "content": query, "sources": [],
                "created_at": datetime.now().isoformat()})
            _chat_histories[session_id].append({
                "id": str(uuid.uuid4()), "role": "assistant", "content": full_response,
                "sources": [{"file_name": s.file_name, "file_ext": s.file_ext,
                             "chunk_text": s.chunk_text, "chunk_index": s.chunk_index, "score": s.score}
                            for s in source_docs],
                "created_at": datetime.now().isoformat()})

            if session_id not in _chat_sessions:
                _chat_sessions[session_id] = {
                    "id": session_id, "title": query[:50], "message_count": 0,
                    "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()}
            _chat_sessions[session_id]["message_count"] = len(_chat_histories[session_id])
            _chat_sessions[session_id]["updated_at"] = datetime.now().isoformat()

            # Step 7: Final chunk with sources
            await context.write(chat_pb2.RagChatChunk(
                token="", finished=True, sources=source_docs,
                message_id=message_id, session_id=session_id))

            logger.info(f"RagChat complete: session={session_id}, response_len={len(full_response)}, sources={len(source_docs)}")

        except Exception as e:
            logger.error(f"RagChat failed: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def GetChatHistory(self, request, context):
        try:
            session_id = request.session_id
            limit = request.limit or 50
            history = _chat_histories.get(session_id, [])[-limit:]

            records = []
            for h in history:
                sources = [common_pb2.SourceDoc(
                    file_name=s.get("file_name", ""), file_ext=s.get("file_ext", ""),
                    chunk_text=s.get("chunk_text", ""), chunk_index=s.get("chunk_index", 0),
                    score=s.get("score", 0.0)) for s in h.get("sources", [])]
                records.append(chat_pb2.ChatHistoryRecord(
                    id=h.get("id", ""), role=h.get("role", ""),
                    content=h.get("content", ""), sources=sources,
                    created_at=h.get("created_at", "")))

            session = _chat_sessions.get(session_id, {})
            return chat_pb2.GetChatHistoryResponse(
                messages=records, session_id=session_id, title=session.get("title", ""))

        except Exception as e:
            logger.error(f"GetChatHistory failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return chat_pb2.GetChatHistoryResponse()

    async def ListChatSessions(self, request, context):
        try:
            sessions = [chat_pb2.ChatSessionInfo(
                id=session_id, title=info.get("title", ""),
                message_count=info.get("message_count", 0),
                created_at=info.get("created_at", ""),
                updated_at=info.get("updated_at", ""))
                for session_id, info in _chat_sessions.items()]
            sessions.sort(key=lambda s: s.updated_at, reverse=True)
            return chat_pb2.ListChatSessionsResponse(sessions=sessions)
        except Exception as e:
            logger.error(f"ListChatSessions failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return chat_pb2.ListChatSessionsResponse()

    async def DeleteChatSession(self, request, context):
        try:
            session_id = request.session_id
            _chat_sessions.pop(session_id, None)
            _chat_histories.pop(session_id, None)
            logger.info(f"Chat session deleted: {session_id}")
            return common_pb2.StatusResponse(success=True, message=f"Session '{session_id}' deleted")
        except Exception as e:
            logger.error(f"DeleteChatSession failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.StatusResponse(success=False, message=str(e))
