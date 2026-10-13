package com.platform.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "checkpoints", indexes = {
    @Index(name = "idx_checkpoint_task_turn", columnList = "taskId, turnIndex")
})
public class CheckpointEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String taskId;

    @Column(nullable = false)
    private int turnIndex;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String messagesJson;

    @Column(columnDefinition = "TEXT")
    private String scratchpadJson;

    @Column(columnDefinition = "TEXT")
    private String diskDiffSummary;

    private int tokensUsed;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    public CheckpointEntity() {}

    public CheckpointEntity(String taskId, int turnIndex, String messagesJson, String scratchpadJson, String diskDiffSummary, int tokensUsed) {
        this.taskId = taskId;
        this.turnIndex = turnIndex;
        this.messagesJson = messagesJson;
        this.scratchpadJson = scratchpadJson;
        this.diskDiffSummary = diskDiffSummary;
        this.tokensUsed = tokensUsed;
        this.createdAt = Instant.now();
    }

    public Long getId() { return id; }
    public String getTaskId() { return taskId; }
    public int getTurnIndex() { return turnIndex; }
    public String getMessagesJson() { return messagesJson; }
    public String getScratchpadJson() { return scratchpadJson; }
    public String getDiskDiffSummary() { return diskDiffSummary; }
    public int getTokensUsed() { return tokensUsed; }
    public Instant getCreatedAt() { return createdAt; }
}
