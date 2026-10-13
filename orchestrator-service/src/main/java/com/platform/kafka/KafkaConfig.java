package com.platform.kafka;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

@Configuration
public class KafkaConfig {

    public static final String TOPIC_INBOUND_TASKS = "agent.tasks.inbound";
    public static final String TOPIC_TASK_EVENTS = "agent.tasks.events";
    public static final String TOPIC_TASK_DLQ = "agent.tasks.dlq";

    @Bean
    public NewTopic inboundTasksTopic() {
        return TopicBuilder.name(TOPIC_INBOUND_TASKS)
                .partitions(3)
                .replicas(1)
                .build();
    }

    @Bean
    public NewTopic taskEventsTopic() {
        return TopicBuilder.name(TOPIC_TASK_EVENTS)
                .partitions(3)
                .replicas(1)
                .build();
    }

    @Bean
    public NewTopic taskDlqTopic() {
        return TopicBuilder.name(TOPIC_TASK_DLQ)
                .partitions(1)
                .replicas(1)
                .build();
    }
}
