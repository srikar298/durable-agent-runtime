# Architectural Specification: Durable Agent Runtime

## 1. System Intent & Scope
The **Durable Agent Runtime** provides a resilient execution environment for multi-step autonomous LLM agents that execute actions over prolonged durations (minutes to hours).

Rather than framing agentic execution as a continuous chat loop, this runtime frames it as a **durable state machine** equipped with transactional checkpoints, external environment validation, and isolated command execution.

---

## 2. Core Subsystems

### 2.1. Checkpoint & Resume Mechanism
* **State Serialization**: At the completion of every atomic turn, the runtime serializes:
  - `session_id`: Unique identifier for the long-running task.
  - `turn_index`: Monotonically increasing sequence number.
  - `message_history`: Complete OpenAI/Anthropic/Gemini compatible message array.
  - `scratchpad_state`: Key-value variables stored by the agent across turns.
  - `disk_diff`: Git status or modified file hashes generated during the turn.
* **Storage Engine**: SQLite in WAL (Write-Ahead Logging) mode for single-node deployments; PostgreSQL for distributed cloud execution.
* **Crash Replay**:
  - Upon startup with an existing `session_id`, the runtime queries the latest valid checkpoint.
  - Reconstructs in-memory state and verifies filesystem coherence before sending the next model prompt.

### 2.2. Ralph Loop (Outer Control) vs. ReAct (Inner Reasoner)
* **The Problem with ReAct Alone**: LLMs frequently claim "Task complete!" when unit tests still fail or syntax errors remain.
* **The Ralph Loop Principle**:
  - The outer loop is an algorithmic controller, not an LLM.
  - Format: `while not completion_criteria_satisfied() and step < max_steps: step()`
  - Completion criteria are hard deterministic commands (e.g. `pytest src/tests` returning exit code 0).
  - The agent's memory is rooted in the repository itself rather than solely in prompt token history.

### 2.3. Sandboxing & Tool Safety
* **Subprocess Confinement**:
  - Any shell or Python script execution runs in an ephemeral child subprocess.
  - Memory caps (via `resource.setrlimit` on Linux or Job Objects on Windows).
  - Hard timeouts (default 30 seconds) to prevent infinite loops (e.g. `while True: pass`).
* **Tool Idempotency**:
  - Each tool call carries an `idempotency_key` derived from `hash(session_id, turn_index, tool_name, args)`.
  - Guarantees that retrying a dropped turn never re-executes external side-effects twice.

### 2.4. Human-in-the-Loop (HITL) Protocol
* Tools are assigned a safety rating:
  1. `READ_ONLY` (e.g., `read_file`, `grep_code`, `list_dir`): Instant automatic execution.
  2. `MUTATION` (e.g., `write_file`, `git_commit`): Logged with diff capture.
  3. `CRITICAL` (e.g., `git_push`, `drop_table`, `http_post_webhook`): Triggers an execution pause and emits an event requiring human sign-off.

---

## 3. Failure Mode Matrix

| Failure Mode | Root Cause | Runtime Mitigation |
| :--- | :--- | :--- |
| **Worker Eviction / Host Crash** | Kubernetes pod kill or OOM. | Resumes from latest SQLite/Postgres checkpoint upon restart. |
| **Context Window Overflow** | Long tool output filling context. | Rolling summarization and tool-output truncation with disk offload. |
| **Tool Ping-Pong Oscillation** | Ambiguous prompt instructions. | Cycle-detection heuristic; forces replanning after 3 repeated turns. |
| **Dangerous Shell Commands** | Malicious injection or hallucination. | AST / Command allow-listing and interactive approval gate. |
