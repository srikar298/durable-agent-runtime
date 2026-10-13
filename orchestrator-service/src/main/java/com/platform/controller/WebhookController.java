package com.platform.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.platform.dto.TaskRequest;
import com.platform.dto.TaskResponse;
import com.platform.model.TaskEntity;
import com.platform.model.TaskStatus;
import com.platform.repository.TaskRepository;
import com.platform.kafka.TaskProducer;
import com.platform.service.DeduplicationService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Optional;

@RestController
@RequestMapping("/api/v1/webhooks")
public class WebhookController {

    private static final Logger log = LoggerFactory.getLogger(WebhookController.class);

    private final TaskRepository taskRepository;
    private final DeduplicationService dedupeService;
    private final TaskProducer taskProducer;
    private final ObjectMapper objectMapper;

    public WebhookController(TaskRepository taskRepository,
                             DeduplicationService dedupeService,
                             TaskProducer taskProducer,
                             ObjectMapper objectMapper) {
        this.taskRepository = taskRepository;
        this.dedupeService = dedupeService;
        this.taskProducer = taskProducer;
        this.objectMapper = objectMapper;
    }

    @PostMapping("/tasks")
    public ResponseEntity<TaskResponse> ingestTask(@Valid @RequestBody TaskRequest request) {
        String source = request.source() != null ? request.source() : "generic-webhook";
        String dedupeKey = request.dedupeKey() != null ? request.dedupeKey() : request.title() + ":" + request.description();
        String dedupeHash = dedupeService.computeFingerprint(source, dedupeKey);

        // 1. Check Redis Deduplication Lock
        boolean isUnique = dedupeService.acquireDeduplicationLock(dedupeHash);
        if (!isUnique) {
            log.warn("Duplicate task detected with hash [{}]. Suppressing re-execution.", dedupeHash);
            Optional<TaskEntity> existing = taskRepository.findByDedupeHash(dedupeHash);
            if (existing.isPresent()) {
                TaskEntity t = existing.get();
                return ResponseEntity.ok(new TaskResponse(t.getId(), t.getTitle(), t.getStatus(), true, t.getCreatedAt()));
            }
        }

        // 2. Persist in PostgreSQL State Machine
        TaskEntity newTask = new TaskEntity(
            request.title(),
            request.description(),
            dedupeHash,
            "{\"source\": \"" + source + "\"}"
        );
        TaskEntity saved = taskRepository.save(newTask);

        // 3. Publish to Apache Kafka (Asynchronous Decoupled Execution)
        try {
            String taskPayloadJson = objectMapper.writeValueAsString(saved);
            taskProducer.publishTask(saved.getId(), taskPayloadJson);
        } catch (Exception e) {
            log.error("Failed to serialize task for Kafka", e);
            saved.setStatus(TaskStatus.FAILED);
            taskRepository.save(saved);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }

        log.info("Task [{}] successfully accepted and queued via Kafka.", saved.getId());
        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .body(new TaskResponse(saved.getId(), saved.getTitle(), saved.getStatus(), false, saved.getCreatedAt()));
    }
}
