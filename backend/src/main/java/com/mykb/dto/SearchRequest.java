package com.mykb.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;

public record SearchRequest(
        @NotBlank(message = "Query is required")
        String query,

        @Min(value = 1, message = "Knowledge base ID is required")
        Long kbId,

        int topK,

        double scoreThreshold,

        String searchMode
) {
    public SearchRequest {
        if (topK <= 0) {
            topK = 5;
        }
        if (scoreThreshold <= 0) {
            scoreThreshold = 0.5;
        }
        if (searchMode == null || searchMode.isBlank()) {
            searchMode = "vector";
        }
    }
}
