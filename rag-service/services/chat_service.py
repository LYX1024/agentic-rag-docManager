"""gRPC ChatService implementation with RAG streaming chat."""
import uuid
import time
from pathlib import Path
from datetime import datetime

import grpc
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

# In-memory chat session store (per process)
_chat_sessions: dict[str, dict] = {}
_chat_histories: dict[str, list[dict]] = {}


class ChatServicer(chat_pb2_grpc.ChatServiceServicer):
    """Chat service with RAG: retrieve + LLM streaming."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.persist_dir = Path(config.vector_store.persist_directory)
        self._embedding_client: EmbeddingClient | None = None
        self._reranker: Reranker | None = None
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

    def _get_reranker(self) -> Reranker:
        if self._reranker is None:
            self._reranker = Reranker(model_name=self.config.reranker.model_name)
        return self._reranker

    def _get_hybrid_retriever(self, kb_name: str) -> HybridRetriever:
        if kb_name not in self._retrievers:
            kb_svc = KBServiceFactory.get_service(
                kb_name=kb_name,
                vs_type=self.config.vector_store.type,
                persist_dir=str(self.persist_dir),
            )
            self._retrievers[kb_name] = HybridRetriever(
                kb_service=kb_svc,
                embedding_client=self.embedding_client,
                bm25_weight=self.config.retriever.bm25_weight,
                vector_weight=self.config.retriever.vector_weight,
                rrf_k=self.config.retriever.rrf_k,
            )
        return self._retrievers[kb_name]

    def _get_kb_name(self, kb_id: int) -> str:
        """Resolve kb_id to kb_name via the registry."""
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
        """Build the RAG prompt from template."""
        return RAG_PROMPT_TEMPLATE.format(context=context_text, query=query)

    def RagChat(self, request, context):
        """Streaming RAG chat: retrieve context, build prompt, stream LLM response.

        Yields RagChatChunk proto messages for each token from the LLM.
        The final chunk includes finished=True and the source documents.
        """
        try:
            query = request.query
            kb_name = request.kb_name if request.kb_name else self._get_kb_name(request.kb_id)
            top_k = request.top_k or self.config.retriever.top_k
            score_threshold = request.score_threshold or self.config.retriever.score_threshold
            session_id = request.session_id or str(uuid.uuid4())
            llm_model = request.llm_model or self.config.llm.model
            temperature = request.temperature or self.config.llm.temperature

            if not query:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Query is required")

            message_id = str(uuid.uuid4())
            logger.info(f"RagChat: session={session_id}, query='{query[:60]}...'")

            # Step 1: Retrieve relevant chunks
            retriever = self._get_hybrid_retriever(kb_name)
            retrieved = retriever.retrieve(
                query=query,
                top_k=top_k,
                score_threshold=score_threshold,
            )

            # Step 2: Optionally re-rank
            if self.config.reranker.enabled and len(retrieved) > self.config.reranker.top_n:
                reranker = self._get_reranker()
                retrieved = reranker.rerank(
                    query=query,
                    candidates=retrieved,
                    top_n=self.config.reranker.top_n,
                )
                logger.debug(f"Re-ranked to {len(retrieved)} chunks")

            # Step 3: Build context string
            chunks_texts = []
            for i, chunk in enumerate(retrieved):
                chunks_texts.append(f"[{i + 1}] {chunk['text']}")
            context_text = "\n\n".join(chunks_texts) if chunks_texts else "暂无相关参考资料。"

            # Step 4: Build full prompt
            prompt = self._build_prompt(query=query, context_text=context_text)

            # Build messages for LLM
            messages = []
            # Include chat history if available
            history = _chat_histories.get(session_id, [])
            for h in history:
                messages.append({"role": h["role"], "content": h["content"]})
            # Add current user query wrapped in RAG prompt
            messages.append({"role": "user", "content": prompt})

            # Step 5: Build source docs for the response
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

            # Step 6: Stream from LLM
            full_response = ""
            try:
                from openai import OpenAI

                llm_client = OpenAI(
                    base_url=self.config.llm.api_base,
                    api_key=self.config.llm.api_key,
                )

                stream = llm_client.chat.completions.create(
                    model=llm_model,
                    messages=messages,
                    temperature=temperature,
                    stream=True,
                )

                for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            token = delta.content
                            full_response += token
                            yield chat_pb2.RagChatChunk(
                                token=token,
                                finished=False,
                                sources=[],
                                message_id=message_id,
                                session_id=session_id,
                            )

            except Exception as llm_err:
                logger.error(f"LLM streaming failed: {llm_err}")
                error_msg = f"[错误] 大模型调用失败: {str(llm_err)}"
                yield chat_pb2.RagChatChunk(
                    token=error_msg,
                    finished=True,
                    sources=source_docs,
                    message_id=message_id,
                    session_id=session_id,
                )
                # Don't re-raise; we yield the error and finish

            # Step 7: Save chat history
            if session_id not in _chat_histories:
                _chat_histories[session_id] = []
            _chat_histories[session_id].append({
                "id": message_id,
                "role": "user",
                "content": query,
                "sources": [],
                "created_at": datetime.now().isoformat(),
            })
            _chat_histories[session_id].append({
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": full_response,
                "sources": [
                    {
                        "file_name": s.file_name,
                        "file_ext": s.file_ext,
                        "chunk_text": s.chunk_text,
                        "chunk_index": s.chunk_index,
                        "score": s.score,
                    }
                    for s in source_docs
                ],
                "created_at": datetime.now().isoformat(),
            })

            # Update session metadata
            if session_id not in _chat_sessions:
                _chat_sessions[session_id] = {
                    "id": session_id,
                    "title": query[:50] + ("..." if len(query) > 50 else ""),
                    "message_count": 0,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
            _chat_sessions[session_id]["message_count"] = len(_chat_histories[session_id])
            _chat_sessions[session_id]["updated_at"] = datetime.now().isoformat()

            # Step 8: Yield final chunk with sources
            yield chat_pb2.RagChatChunk(
                token="",
                finished=True,
                sources=source_docs,
                message_id=message_id,
                session_id=session_id,
            )

            logger.info(
                f"RagChat complete: session={session_id}, "
                f"response_len={len(full_response)}, sources={len(source_docs)}"
            )

        except Exception as e:
            logger.error(f"RagChat failed: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))

    def GetChatHistory(self, request, context):
        """Get the chat history for a session."""
        try:
            session_id = request.session_id
            limit = request.limit or 50

            history = _chat_histories.get(session_id, [])
            # Return the most recent messages
            history = history[-limit:]

            records = []
            for h in history:
                sources = []
                for s in h.get("sources", []):
                    sources.append(common_pb2.SourceDoc(
                        file_name=s.get("file_name", ""),
                        file_ext=s.get("file_ext", ""),
                        chunk_text=s.get("chunk_text", ""),
                        chunk_index=s.get("chunk_index", 0),
                        score=s.get("score", 0.0),
                    ))

                records.append(chat_pb2.ChatHistoryRecord(
                    id=h.get("id", ""),
                    role=h.get("role", ""),
                    content=h.get("content", ""),
                    sources=sources,
                    created_at=h.get("created_at", ""),
                ))

            session = _chat_sessions.get(session_id, {})
            title = session.get("title", "")

            return chat_pb2.GetChatHistoryResponse(
                messages=records,
                session_id=session_id,
                title=title,
            )

        except Exception as e:
            logger.error(f"GetChatHistory failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return chat_pb2.GetChatHistoryResponse()

    def ListChatSessions(self, request, context):
        """List all chat sessions."""
        try:
            sessions = []
            # If kb_id is specified, we could filter, but sessions are global for now
            for session_id, info in _chat_sessions.items():
                sessions.append(chat_pb2.ChatSessionInfo(
                    id=session_id,
                    title=info.get("title", ""),
                    message_count=info.get("message_count", 0),
                    created_at=info.get("created_at", ""),
                    updated_at=info.get("updated_at", ""),
                ))

            # Sort by updated_at descending
            sessions.sort(key=lambda s: s.updated_at, reverse=True)

            return chat_pb2.ListChatSessionsResponse(sessions=sessions)

        except Exception as e:
            logger.error(f"ListChatSessions failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return chat_pb2.ListChatSessionsResponse()

    def DeleteChatSession(self, request, context):
        """Delete a chat session and its history."""
        try:
            session_id = request.session_id

            if session_id in _chat_sessions:
                del _chat_sessions[session_id]

            if session_id in _chat_histories:
                del _chat_histories[session_id]

            logger.info(f"Chat session deleted: {session_id}")

            return common_pb2.StatusResponse(
                success=True,
                message=f"Session '{session_id}' deleted",
            )

        except Exception as e:
            logger.error(f"DeleteChatSession failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.StatusResponse(success=False, message=str(e))
