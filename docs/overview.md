# Architectural Specification: Event-Driven Agent Platform

## 1. System Intent & Scope
The **Event-Driven Agent Platform** is an enterprise-scale architecture for ingesting, queueing, and orchestrating autonomous AI agent tasks at scale.

It couples **Java 21 / Spring Boot 3** for high-throughput webhook ingestion, transaction management, deduplication, and Kafka message routing, with a **Python 3.12 Worker Pool** executing sandboxed ReAct/Ralph agentic loops.

---

## 2. Pragmatic System Design Rationale

### 2.1. Why Decouple with Apache Kafka?
* **Problem**: Incoming events (e.g. GitHub PR webhooks, PagerDuty incidents, customer triage tickets) are bursty and unpredictable. LLM inference calls require $3-15\text{s}$ per turn, and a complete multi-step agent run can take $1-5\text{ minutes}$.
* **Solution**: 
  - The Spring Boot webhook endpoint acknowledges incoming HTTP POSTs in $< 20\text{ms}$ with `202 Accepted` after generating a persistent task record.
  - Events are partitioned into Kafka by `task_id` or `repo_id`.
  - Python worker pools subscribe via a consumer group, processing tasks with backpressure.
  - If a worker dies, Kafka reassigns the partition without message loss.

### 2.2. Why Alert Deduplication in Redis?
* During major cloud outages or burst commits, monitoring systems fire identical alerts in rapid succession.
* Using Redis atomic key reservation (`SET alert:{hash} EX 300 NX`):
  - First alert is queued for processing.
  - Subsequent 49 duplicate alerts over the next 5 minutes are discarded or appended as secondary metadata without triggering redundant, expensive LLM inferences.

### 2.3. PostgreSQL State Machine & Checkpoint Storage
* Task states are enforced via an explicit state transition engine:
  $$\text{PENDING} \longrightarrow \text{IN_PROGRESS} \longrightarrow \begin{cases} \text{REQUIRES_APPROVAL} \longrightarrow \text{IN_PROGRESS} \\ \text{COMPLETED} \\ \text{FAILED} \longrightarrow \text{DEAD_LETTER} \end{cases}$$
* PostgreSQL tables:
  - `tasks`: Core status, priority, trigger metadata.
  - `checkpoints`: Turn index, token counts, JSONB context snapshots, modified file diffs.
  - `approval_requests`: Pending human decisions with timeout boundaries.

### 2.4. Python Agent Execution Engine
* Each agent worker consumes a task record from Kafka, initializes its local sandbox, and executes the ReAct reasoning loop.
* Interacting with external systems (Bash, file edits, git, HTTP) happens exclusively through bounded tool interfaces.
* When a tool marked `requires_human_approval=True` is selected, the worker transitions the task to `REQUIRES_APPROVAL` in Postgres, pauses execution, and commits an event to Kafka.

---

## 3. Capacity & Throughput Targets

* **Ingestion SLA**: $p99 < 50\text{ms}$ for inbound webhooks.
* **Peak Burst Capacity**: $10,000\text{ webhooks/minute}$ buffered seamlessly in Kafka.
* **Agent Task Concurrency**: Horizontally scalable Python worker pods bounded by LLM provider rate limits (RPM / TPM).
* **Fault Tolerance**: Automatic step resumption from PostgreSQL checkpoints within $< 100\text{ms}$ of worker recovery.
