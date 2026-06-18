package com.mykb.dto;

import jakarta.validation.constraints.NotBlank;

public record KBCreateRequest(
        String name,

        String description,

        String vsType,

        String embedModel
) {}
