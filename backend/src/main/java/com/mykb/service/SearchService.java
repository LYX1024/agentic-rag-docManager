package com.mykb.service;

import com.mykb.dto.SearchRequest;
import com.mykb.grpc.client.SearchClient;
import com.mykb.proto.search.SearchService;
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
        SearchService.SearchResponse grpcResponse = searchClient.search(
                request.query(), request.kbId(), request.topK(), request.scoreThreshold());

        List<Map<String, Object>> results = new ArrayList<>();
        for (SearchService.SearchResult result : grpcResponse.getResultsList()) {
            Map<String, Object> item = new HashMap<>();
            item.put("docId", result.getDocId());
            item.put("content", result.getContent());
            item.put("score", result.getScore());
            item.put("metadata", result.getMetadataMap());
            results.add(item);
        }

        Map<String, Object> response = new HashMap<>();
        response.put("query", request.query());
        response.put("results", results);
        response.put("total", results.size());
        log.info("Search completed: query={}, total={}", request.query(), results.size());
        return response;
    }

    public Map<String, Object> hybridSearch(SearchRequest request) {
        SearchService.HybridSearchResponse grpcResponse = searchClient.hybridSearch(
                request.query(), request.kbId(), request.topK(), request.scoreThreshold());

        List<Map<String, Object>> denseResults = new ArrayList<>();
        for (SearchService.SearchResult result : grpcResponse.getDenseResultsList()) {
            Map<String, Object> item = new HashMap<>();
            item.put("docId", result.getDocId());
            item.put("content", result.getContent());
            item.put("score", result.getScore());
            item.put("metadata", result.getMetadataMap());
            denseResults.add(item);
        }

        List<Map<String, Object>> sparseResults = new ArrayList<>();
        for (SearchService.SearchResult result : grpcResponse.getSparseResultsList()) {
            Map<String, Object> item = new HashMap<>();
            item.put("docId", result.getDocId());
            item.put("content", result.getContent());
            item.put("score", result.getScore());
            item.put("metadata", result.getMetadataMap());
            sparseResults.add(item);
        }

        Map<String, Object> response = new HashMap<>();
        response.put("query", request.query());
        response.put("denseResults", denseResults);
        response.put("sparseResults", sparseResults);
        response.put("fusionMethod", grpcResponse.getFusionMethod());
        log.info("HybridSearch completed: query={}, dense={}, sparse={}",
                request.query(), denseResults.size(), sparseResults.size());
        return response;
    }
}
