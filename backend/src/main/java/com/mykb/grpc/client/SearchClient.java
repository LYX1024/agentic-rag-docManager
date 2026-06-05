package com.mykb.grpc.client;

import com.mykb.exception.BusinessException;
import com.mykb.proto.search.HybridSearchRequest;
import com.mykb.proto.search.HybridSearchResponse;
import com.mykb.proto.search.SearchRequest;
import com.mykb.proto.search.SearchResponse;
import com.mykb.proto.search.SearchServiceGrpc;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class SearchClient {

    private final SearchServiceGrpc.SearchServiceBlockingStub stub;

    public SearchResponse search(String query, Long kbId, String kbName, int topK, float scoreThreshold, String searchType) {
        try {
            SearchRequest request = SearchRequest.newBuilder()
                    .setQuery(query)
                    .setKbId(kbId)
                    .setKbName(kbName != null ? kbName : "")
                    .setTopK(topK)
                    .setScoreThreshold(scoreThreshold)
                    .setSearchType(searchType != null ? searchType : "vector")
                    .build();
            SearchResponse response = stub.search(request);
            log.info("gRPC search: query={}, kbId={}, results={}", query, kbId, response.getResultsCount());
            return response;
        } catch (Exception e) {
            log.error("gRPC search failed: query={}, kbId={}, error={}", query, kbId, e.getMessage(), e);
            throw new BusinessException("Failed to search: " + e.getMessage());
        }
    }

    public HybridSearchResponse hybridSearch(String query, Long kbId, String kbName,
                                              int topK, float scoreThreshold) {
        try {
            HybridSearchRequest request = HybridSearchRequest.newBuilder()
                    .setQuery(query)
                    .setKbId(kbId)
                    .setKbName(kbName != null ? kbName : "")
                    .setTopK(topK)
                    .setScoreThreshold(scoreThreshold)
                    .build();
            HybridSearchResponse response = stub.hybridSearch(request);
            log.info("gRPC hybridSearch: query={}, kbId={}, results={}", query, kbId, response.getResultsCount());
            return response;
        } catch (Exception e) {
            log.error("gRPC hybridSearch failed: query={}, kbId={}, error={}", query, kbId, e.getMessage(), e);
            throw new BusinessException("Failed to hybrid search: " + e.getMessage());
        }
    }
}
