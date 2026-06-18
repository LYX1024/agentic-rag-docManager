package com.mykb.service;

import com.mykb.dto.SearchRequest;
import com.mykb.grpc.client.SearchClient;
import com.mykb.proto.search.HybridSearchResponse;
import com.mykb.proto.search.SearchResponse;
import com.mykb.proto.search.SearchResult;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class SearchService {

    private final SearchClient searchClient;

    public Map<String, Object> search(SearchRequest request) {
        SearchResponse grpcResponse = searchClient.search(
                request.query(), request.kbId(), "",
                request.topK(), (float) request.scoreThreshold(), request.searchMode());

        List<Map<String, Object>> results = new ArrayList<>();
        for (SearchResult result : grpcResponse.getResultsList()) {
            results.add(convertResult(result));
        }

        Map<String, Object> response = new HashMap<>();
        response.put("query", request.query());
        response.put("results", results);
        response.put("total", grpcResponse.getTotal());
        response.put("tookMs", grpcResponse.getTookMs());
        log.info("Search completed: query={}, total={}", request.query(), results.size());
        return response;
    }

    public Map<String, Object> hybridSearch(SearchRequest request) {
        HybridSearchResponse grpcResponse = searchClient.hybridSearch(
                request.query(), request.kbId(), "",
                request.topK(), (float) request.scoreThreshold());

        List<Map<String, Object>> results = new ArrayList<>();
        for (SearchResult result : grpcResponse.getResultsList()) {
            results.add(convertResult(result));
        }

        Map<String, Object> response = new HashMap<>();
        response.put("query", request.query());
        response.put("results", results);
        response.put("total", grpcResponse.getTotal());
        response.put("bm25Count", grpcResponse.getBm25Count());
        response.put("vectorCount", grpcResponse.getVectorCount());
        response.put("fusedCount", grpcResponse.getFusedCount());
        response.put("tookMs", grpcResponse.getTookMs());
        log.info("HybridSearch completed: query={}, total={}", request.query(), results.size());
        return response;
    }

    private Map<String, Object> convertResult(SearchResult result) {
        Map<String, Object> item = new HashMap<>();
        item.put("chunkId", result.getChunkId());
        item.put("text", result.getText());
        item.put("score", result.getScore());
        item.put("fileName", result.getFileName());
        item.put("fileExt", result.getFileExt());
        item.put("chunkIndex", result.getChunkIndex());
        return item;
    }
}
