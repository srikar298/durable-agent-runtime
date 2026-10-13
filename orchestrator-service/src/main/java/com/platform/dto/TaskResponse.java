package com.platform.dto;

import com.platform.model.TaskStatus;
import java.time.Instant;

public record TaskResponse(
    String taskId,
    String title,
    TaskStatus status,
    boolean isDuplicate,
    Instant createdAt
) {}
