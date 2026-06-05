package com.mykb.dto;

import jakarta.validation.constraints.NotBlank;

public record KBCreateRequest(
        @NotBlank(message = "Knowledge base name is required")
        String name,

        String description,

        String vsType,

        String embedModel
) {}
