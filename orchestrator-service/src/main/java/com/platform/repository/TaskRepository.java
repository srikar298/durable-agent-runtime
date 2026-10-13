package com.platform.repository;

import com.platform.model.TaskEntity;
import com.platform.model.TaskStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TaskRepository extends JpaRepository<TaskEntity, String> {
    Optional<TaskEntity> findByDedupeHash(String dedupeHash);
    List<TaskStatus> findAllByStatus(TaskStatus status);
}
