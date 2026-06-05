package com.mykb.dto;

import jakarta.validation.constraints.NotNull;

public record ChatSessionCreateRequest(
        String title,

        @NotNull(message = "Knowledge base ID is required")
        Long kbId
) {}
