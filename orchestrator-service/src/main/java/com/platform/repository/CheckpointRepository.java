package com.platform.repository;

import com.platform.model.CheckpointEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface CheckpointRepository extends JpaRepository<CheckpointEntity, Long> {
    List<CheckpointEntity> findAllByTaskIdOrderByTurnIndexAsc(String taskId);
    Optional<CheckpointEntity> findTopByTaskIdOrderByTurnIndexDesc(String taskId);
}
