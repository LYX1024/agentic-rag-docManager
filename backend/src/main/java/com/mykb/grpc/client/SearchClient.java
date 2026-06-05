package com.mykb.grpc.client;

import com.mykb.exception.BusinessException;
import com.mykb.proto.search.SearchServiceGrpc;
import com.mykb.proto.search.SearchService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class SearchClient {

    private final SearchServiceGrpc.SearchServiceBlockingStub stub;

    public SearchService.SearchResponse search(String query, Long kbId, int topK, double scoreThreshold) {
        try {
            SearchService.SearchRequest request = SearchService.SearchRequest.newBuilder()
                    .setQuery(query)
                    .setKbId(kbId.toString())
                    .setTopK(topK)
                    .setScoreThreshold((float) scoreThreshold)
                    .build();
            SearchService.SearchResponse response = stub.search(request);
            log.info("gRPC search success: query={}, kbId={}, results={}", query, kbId, response.getResultsCount());
            return response;
        } catch (Exception e) {
            log.error("gRPC search failed: query={}, kbId={}, error={}", query, kbId, e.getMessage(), e);
            throw new BusinessException("Failed to search: " + e.getMessage());
        }
    }

    public SearchService.HybridSearchResponse hybridSearch(String query, Long kbId, int topK, double scoreThreshold) {
        try {
            SearchService.SearchRequest request = SearchService.SearchRequest.newBuilder()
                    .setQuery(query)
                    .setKbId(kbId.toString())
                    .setTopK(topK)
                    .setScoreThreshold((float) scoreThreshold)
                    .build();
            SearchService.HybridSearchResponse response = stub.hybridSearch(request);
            log.info("gRPC hybridSearch success: query={}, kbId={}, results={}", query, kbId, response.getResultsCount());
            return response;
        } catch (Exception e) {
            log.error("gRPC hybridSearch failed: query={}, kbId={}, error={}", query, kbId, e.getMessage(), e);
            throw new BusinessException("Failed to hybrid search: " + e.getMessage());
        }
    }
}
