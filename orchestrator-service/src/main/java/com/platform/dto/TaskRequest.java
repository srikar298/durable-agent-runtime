package com.platform.dto;

import jakarta.validation.constraints.NotBlank;

public record TaskRequest(
    @NotBlank(message = "Title is required")
    String title,

    @NotBlank(message = "Description / Instruction is required")
    String description,

    String source,
    String dedupeKey
) {}
