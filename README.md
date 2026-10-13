# Durable Agent Runtime ⚡

[![Java 21](https://img.shields.io/badge/java-21%20(Spring%20Boot%203)-red.svg)](https://spring.io/)
[![Python 3.12](https://img.shields.io/badge/python-3.12%20(AI%20Worker)-blue.svg)](https://www.python.org/)
[![Kafka](https://img.shields.io/badge/messaging-Apache%20Kafka-black.svg)](https://kafka.apache.org/)
[![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL%2016-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/cache-Redis%20(Deduplication)-red.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An enterprise-grade, **durable event-driven autonomous agent runtime** built with **Java (Spring Boot 3.x)**, **Apache Kafka**, **PostgreSQL**, **Redis**, and **Python**.

Standard agent frameworks (LangChain, CrewAI, AutoGen) run in-memory loops. If the host process crashes at turn 18 of a 20-step refactor or incident triage, the entire memory context is lost, wasting tokens and leaving partial side-effects.

**Durable Agent Runtime** treats autonomous agents as **durable distributed state machines**: bursty events (GitHub PRs, monitoring alerts) are buffered via **Apache Kafka**, deduplicated via **Redis**, state-managed via **PostgreSQL**, and executed by a **Python worker pool** running sandboxed ReAct and Ralph loops with transactional step checkpoints.

---

## 🎯 Why This Architecture? (Pragmatic Engineering Rationale)

In production, agents are distributed systems with distinct physical requirements:
1. **Bursty Webhooks vs. Slow LLM Inference**: Webhooks arrive in bursts of hundreds per second, while LLM inference takes 3–15 seconds per call. Ingesting synchronously over HTTP crashes services. We use **Java Spring Boot + Apache Kafka** as an elastic shock absorber.
2. **Alert Storm Deduplication**: When an infrastructure incident fires 50 cascading alerts in 2 minutes, we use **Redis `SETNX`** to drop duplicates and acquire distributed locks before burning expensive LLM tokens.
3. **Durable State Machine**: Agent tasks span minutes to hours. We persist task lifecycle states (`PENDING`, `INVESTIGATING`, `REQUIRES_APPROVAL`, `RESOLVED`) in **PostgreSQL** with ACID consistency and turn-level checkpoints.
4. **Sandboxed AI Execution**: The **Python AI Worker** consumes from Kafka, runs the ReAct/Ralph agent loop with sandboxed subprocess tools, and emits events back to Kafka.

---

## 🏗 End-to-End System Architecture

```mermaid
flowchart TD
    Webhooks["Inbound Webhooks<br/>(GitHub PRs / PagerDuty Alerts)"] --> SpringBoot["Java 21 Spring Boot<br/>Ingestion & State Orchestrator"]
    
    subgraph SpringBootLayer ["Spring Boot Core Logic"]
        SpringBoot <--> RedisDedupe["Redis<br/>(Deduplication & Distributed Locks)"]
        SpringBoot <--> PostgresDB["PostgreSQL 16<br/>(Task State Machine & Checkpoints)"]
        SpringBoot --> KafkaProducer["Kafka Event Publisher"]
    end

    KafkaProducer --> KafkaInbound["Kafka Topic:<br/>agent.tasks.inbound<br/>(Partitioned by Task ID)"]

    subgraph WorkerPool ["Python AI Agent Execution Pool"]
        KafkaInbound --> PyWorker["Python Agent Worker<br/>(ReAct + Ralph Loop Engine)"]
        PyWorker --> Sandbox["Sandboxed Subprocess<br/>(Code Execution & File Diffs)"]
        Sandbox --> PyWorker
        PyWorker --> HITL{"High Risk Action?<br/>(Needs Human Approval)"}
        HITL -- Yes --> PauseTask["Emit Event: AWAITING_APPROVAL<br/>To PostgreSQL via REST/Kafka"]
        HITL -- No --> CompleteTask["Execute Action"]
    end

    PyWorker --> KafkaOutbound["Kafka Topic:<br/>agent.tasks.events"]
    KafkaOutbound --> SpringBoot
    SpringBoot --> Notification["Slack / Webhook Notification"]
```

---

## 🚀 Key Modules & Tech Stack

### 1. Ingestion & Orchestrator Service (`orchestrator-service/`)
* **Framework**: Java 21, Spring Boot 3.3+, Spring Kafka, Spring Data JPA.
* **Responsibilities**:
  * High-throughput webhook ingestion endpoints with HMAC signature verification.
  * In-flight alert deduplication via Redis sliding-window hashes.
  * Managing task state transitions in PostgreSQL.
  * Publishing tasks to Kafka topics with retry topics and Dead-Letter Queues (DLQ).
  * WebSocket / SSE endpoint for real-time agent execution progress streaming.

### 2. Autonomous Agent Worker (`agent-worker/`)
* **Framework**: Python 3.12, Pydantic v2, Google GenAI / Anthropic SDK.
* **Responsibilities**:
  * Consumes tasks from Kafka consumer group with manual commit offset management.
  * Executes the **ReAct loop** (Reasoning + Acting) bounded by the **Ralph loop** (external environment verification).
  * Checkpoint persistence: writes execution traces after each turn.
  * Human-in-the-Loop approval gate for critical tools (e.g. cloud remediation commands, git push).

---

## 📊 System Resilience Comparison

| Capability | Naive Single-Script Agent | Durable Agent Runtime |
| :--- | :--- | :--- |
| **Ingestion Capacity** | Fails under burst (>10 concurrent HTTP calls) | **10,000+ req/sec (Buffered via Kafka)** |
| **Alert Storm Behavior** | Fires 50 separate redundant LLM loops | **Deduplicated in Redis (<5ms)** |
| **Worker Crash During Turn 8** | All context and work lost | **Resumes cleanly from PostgreSQL checkpoint** |
| **High-Risk Tool Safety** | Unrestricted shell execution | **Paused via State Machine for Human Sign-off** |

---

## 📁 Repository Structure

```text
durable-agent-runtime/
├── .github/workflows/ci.yml           # CI for Java & Python services
├── orchestrator-service/              # Java 21 / Spring Boot 3.x
│   ├── pom.xml                        # Maven dependencies (Spring Kafka, Data JPA, Redis)
│   └── src/main/java/com/platform/
│       ├── controller/                # Webhook & Approval REST endpoints
│       ├── service/                   # Task orchestrator & Redis deduplicator
│       ├── kafka/                     # Kafka producers, consumers & DLQ configs
│       └── model/                     # JPA entities (Task, StepAudit, Approval)
├── agent-worker/                      # Python 3.12 AI Worker
│   ├── pyproject.toml                 # Dependencies (Pydantic, Kafka, LLM SDKs)
│   └── src/
│       ├── consumer.py                # Kafka task listener with manual commits
│       ├── agent_loop.py              # ReAct / Ralph loop orchestrator
│       ├── checkpoint.py              # Task state checkpointing
│       └── sandbox.py                 # Subprocess execution sandbox
├── docs/
│   ├── overview.md                    # Detailed architectural specification
│   └── adr/                           # Architectural Decision Records
├── docker-compose.yml                 # Kafka, Zookeeper, PostgreSQL & Redis setup
└── README.md
```

---

## 🛠 Quickstart

### 1. Start Infrastructure (Kafka, Postgres, Redis)
```bash
docker compose up -d
```

### 2. Start the Spring Boot Orchestrator
```bash
cd orchestrator-service
./mvnw spring-boot:run
```

### 3. Start the Python Agent Worker
```bash
cd ../agent-worker
pip install -e .
python -m src.consumer
```

---

## 📜 Architectural Decision Records (ADRs)
- [ADR-001: Kafka for Asynchronous LLM Task Decoupling](docs/adr/001-kafka-decoupling.md)
- [ADR-002: Redis Deduplication during Incident Alert Storms](docs/adr/002-redis-deduplication.md)
- [ADR-003: Polyglot Java-Python System Boundary Design](docs/adr/003-polyglot-boundary.md)
