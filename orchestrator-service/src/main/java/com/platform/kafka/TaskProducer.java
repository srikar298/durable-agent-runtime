package com.platform.kafka;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
public class TaskProducer {

    private static final Logger log = LoggerFactory.getLogger(TaskProducer.class);
    private final KafkaTemplate<String, String> kafkaTemplate;

    public TaskProducer(KafkaTemplate<String, String> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    public void publishTask(String taskId, String taskJson) {
        log.info("Publishing task [{}] to topic [{}]", taskId, KafkaConfig.TOPIC_INBOUND_TASKS);
        kafkaTemplate.send(KafkaConfig.TOPIC_INBOUND_TASKS, taskId, taskJson)
            .whenComplete((result, ex) -> {
                if (ex != null) {
                    log.error("Failed to publish task [{}] to Kafka", taskId, ex);
                } else {
                    log.info("Task [{}] successfully sent to partition [{}]", taskId, result.getRecordMetadata().partition());
                }
            });
    }
}
