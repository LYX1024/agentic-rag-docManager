"""gRPC SearchService implementation."""
import time
from pathlib import Path

import grpc
from loguru import logger

from config.model_config import AppConfig
from embedding.embed_model import EmbeddingClient
from kb_service.kb_service import KBServiceFactory
from retriever.bm25_retriever import BM25Retriever
from retriever.vector_retriever import VectorRetriever
from retriever.hybrid_retriever import HybridRetriever
from retriever.reranker import Reranker

from generated import search_pb2
from generated import search_pb2_grpc
from generated import common_pb2


class SearchServicer(search_pb2_grpc.SearchServiceServicer):
    """Search service: vector search, hybrid search, and re-rank."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.persist_dir = Path(config.vector_store.persist_directory)
        self._embedding_client: EmbeddingClient | None = None
        self._reranker: Reranker | None = None
        # Cache hybrid retrievers per KB name
        self._retrievers: dict[str, HybridRetriever] = {}
        logger.info("SearchServicer initialized")

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

    def _build_search_result(self, item: dict) -> search_pb2.SearchResult:
        """Convert an internal result dict to a SearchResult proto."""
        metadata = item.get("metadata", {})
        return search_pb2.SearchResult(
            chunk_id=item.get("id", ""),
            text=item.get("text", ""),
            score=item.get("score", 0.0),
            file_name=metadata.get("source_file", ""),
            file_ext=metadata.get("source_ext", ""),
            chunk_index=metadata.get("chunk_index", 0),
            vs_doc_id=item.get("id", ""),
        )

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

    def Search(self, request, context):
        """Perform a single-strategy search (vector or BM25)."""
        try:
            query = request.query
            kb_name = request.kb_name if request.kb_name else self._get_kb_name(request.kb_id)
            top_k = request.top_k or self.config.retriever.top_k
            score_threshold = request.score_threshold or self.config.retriever.score_threshold
            search_type = request.search_type or "vector"

            if not query:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Query is required")
                return search_pb2.SearchResponse()

            kb_svc = KBServiceFactory.get_service(
                kb_name=kb_name,
                vs_type=self.config.vector_store.type,
                persist_dir=str(self.persist_dir),
            )

            start_time = time.time()

            if search_type == "bm25":
                bm25 = BM25Retriever(kb_svc)
                results = bm25.search(query, top_k=top_k)
            else:
                vector = VectorRetriever(kb_svc, self.embedding_client)
                results = vector.search(query, top_k=top_k, score_threshold=score_threshold)

            took_ms = int((time.time() - start_time) * 1000)

            search_results = [self._build_search_result(r) for r in results]

            logger.info(
                f"Search: type={search_type}, query='{query[:50]}...' "
                f"-> {len(search_results)} results, {took_ms}ms"
            )

            return search_pb2.SearchResponse(
                results=search_results,
                total=len(search_results),
                search_type=search_type,
                took_ms=took_ms,
            )

        except Exception as e:
            logger.error(f"Search failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return search_pb2.SearchResponse()

    def HybridSearch(self, request, context):
        """Perform hybrid search (BM25 + Vector RRF fusion), optionally with re-ranking."""
        try:
            query = request.query
            kb_name = request.kb_name if request.kb_name else self._get_kb_name(request.kb_id)
            top_k = request.top_k or self.config.retriever.top_k
            score_threshold = request.score_threshold or self.config.retriever.score_threshold
            bm25_weight = request.bm25_weight or self.config.retriever.bm25_weight
            vector_weight = request.vector_weight or self.config.retriever.vector_weight
            rrf_k = request.rrf_k or self.config.retriever.rrf_k

            if not query:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Query is required")
                return search_pb2.HybridSearchResponse()

            start_time = time.time()

            # Create a custom hybrid retriever with the specified weights
            kb_svc = KBServiceFactory.get_service(
                kb_name=kb_name,
                vs_type=self.config.vector_store.type,
                persist_dir=str(self.persist_dir),
            )

            hybrid = HybridRetriever(
                kb_service=kb_svc,
                embedding_client=self.embedding_client,
                bm25_weight=bm25_weight,
                vector_weight=vector_weight,
                rrf_k=rrf_k,
            )

            # Retrieve 2x for better recall before re-ranking
            fetch_k = top_k * 2
            fused_results = hybrid.retrieve(
                query=query,
                top_k=fetch_k,
                score_threshold=score_threshold,
            )

            bm25_count = 0
            vector_count = 0

            # Apply re-ranking if requested
            reranked_count = 0
            if request.use_reranker:
                reranker_model = request.reranker_model or self.config.reranker.model_name
                rerank_top_n = request.rerank_top_n or self.config.reranker.top_n
                if reranker_model != self.config.reranker.model_name:
                    reranker = Reranker(model_name=reranker_model)
                else:
                    reranker = self._get_reranker()

                fused_results = reranker.rerank(query=query, candidates=fused_results, top_n=rerank_top_n)
                reranked_count = len(fused_results)

            # Trim to top_k
            fused_results = fused_results[:top_k]

            took_ms = int((time.time() - start_time) * 1000)

            search_results = [self._build_search_result(r) for r in fused_results]

            logger.info(
                f"HybridSearch: query='{query[:50]}...' "
                f"-> fused={len(search_results)}, reranked={reranked_count}, {took_ms}ms"
            )

            return search_pb2.HybridSearchResponse(
                results=search_results,
                total=len(search_results),
                bm25_count=bm25_count,
                vector_count=vector_count,
                fused_count=len(fused_results),
                reranked_count=reranked_count,
                took_ms=took_ms,
            )

        except Exception as e:
            logger.error(f"HybridSearch failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return search_pb2.HybridSearchResponse()

    def Rerank(self, request, context):
        """Re-rank a list of candidate chunks."""
        try:
            query = request.query
            top_n = request.top_n or self.config.reranker.top_n
            model_name = request.model_name or self.config.reranker.model_name

            if not query:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Query is required")
                return search_pb2.RerankResponse()

            # Convert proto ChunkInfo to internal format
            candidates = []
            for c in request.candidates:
                candidates.append({
                    "id": c.chunk_id,
                    "text": c.text,
                    "score": float(c.score),
                    "metadata": {},
                })

            start_time = time.time()

            if model_name != self.config.reranker.model_name:
                reranker = Reranker(model_name=model_name)
            else:
                reranker = self._get_reranker()

            reranked = reranker.rerank(query=query, candidates=candidates, top_n=top_n)

            took_ms = int((time.time() - start_time) * 1000)

            ranked_chunks = []
            for i, r in enumerate(reranked):
                ranked_chunks.append(common_pb2.ChunkInfo(
                    chunk_id=r.get("id", ""),
                    text=r.get("text", ""),
                    index=i,
                    file_id="",
                    score=r.get("rerank_score", r.get("score", 0.0)),
                ))

            logger.info(
                f"Rerank: {len(candidates)} candidates -> top {len(ranked_chunks)}, {took_ms}ms"
            )

            return search_pb2.RerankResponse(
                ranked_results=ranked_chunks,
                took_ms=took_ms,
            )

        except Exception as e:
            logger.error(f"Rerank failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return search_pb2.RerankResponse()
