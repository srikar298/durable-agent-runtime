import json
import logging
import signal
import sys
from kafka import KafkaConsumer
from .models import InboundTaskPayload
from .checkpoint import CheckpointStore
from .sandbox import SubprocessSandbox
from .agent_loop import DurableAgentLoop

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("kafka_worker")


def run_worker(bootstrap_servers: str = "localhost:9092", topic: str = "agent.tasks.inbound"):
    logger.info(f"Connecting to Kafka [{bootstrap_servers}], listening on topic [{topic}]")

    checkpoint_store = CheckpointStore(db_path="./data/worker_checkpoints.db")
    sandbox = SubprocessSandbox(workspace_dir="./data/sandbox")
    agent_loop = DurableAgentLoop(checkpoint_store=checkpoint_store, sandbox=sandbox)

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="python-agent-worker-group",
        enable_auto_commit=False,  # Manual commit ensures zero message loss on worker failure
        auto_offset_reset="earliest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8"))
    )

    def handle_shutdown(signum, frame):
        logger.info("Graceful shutdown signal received. Closing Kafka consumer.")
        consumer.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("Ready to process tasks from Kafka.")
    for message in consumer:
        try:
            task_dict = message.value
            task = InboundTaskPayload(
                id=task_dict.get("id", str(message.offset)),
                title=task_dict.get("title", "Untitled"),
                description=task_dict.get("description", "")
            )
            logger.info(f"Received task [{task.id}]: {task.title}")

            # Execute durable agentic loop
            result = agent_loop.execute(task_id=task.id, instruction=task.description)
            logger.info(f"Completed task [{task.id}] with status [{result.status}]")

            # Commit offset only after successful checkpointing
            consumer.commit()

        except Exception as e:
            logger.error(f"Error processing message at offset [{message.offset}]: {e}", exc_info=True)


if __name__ == "__main__":
    run_worker()
