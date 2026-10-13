import sqlite3
import json
import os
from typing import Optional, List
from .models import CheckpointData, Message


class CheckpointStore:
    """
    Transactional checkpoint engine for agent execution turns.
    Stores complete message histories, token counters, and scratchpad state.
    """

    def __init__(self, db_path: str = "./checkpoints.db"):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode = WAL")  # Sub-millisecond concurrent writes
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    messages_json TEXT NOT NULL,
                    scratchpad_json TEXT NOT NULL,
                    disk_diff_summary TEXT,
                    tokens_consumed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(task_id, turn_index)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_turn ON agent_checkpoints(task_id, turn_index)")

    def save_checkpoint(self, checkpoint: CheckpointData):
        messages_raw = [m.model_dump() for m in checkpoint.messages]
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO agent_checkpoints 
                (task_id, turn_index, status, messages_json, scratchpad_json, disk_diff_summary, tokens_consumed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                checkpoint.task_id,
                checkpoint.turn_index,
                checkpoint.status,
                json.dumps(messages_raw),
                json.dumps(checkpoint.scratchpad),
                checkpoint.disk_diff_summary,
                checkpoint.tokens_consumed,
                checkpoint.created_at
            ))

    def load_latest_checkpoint(self, task_id: str) -> Optional[CheckpointData]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT task_id, turn_index, status, messages_json, scratchpad_json, disk_diff_summary, tokens_consumed, created_at
                FROM agent_checkpoints
                WHERE task_id = ?
                ORDER BY turn_index DESC
                LIMIT 1
            """, (task_id,))
            row = cursor.fetchone()
            if not row:
                return None

            raw_messages = json.loads(row["messages_json"])
            messages = [Message(**m) for m in raw_messages]

            return CheckpointData(
                task_id=row["task_id"],
                turn_index=row["turn_index"],
                status=row["status"],
                messages=messages,
                scratchpad=json.loads(row["scratchpad_json"]),
                disk_diff_summary=row["disk_diff_summary"],
                tokens_consumed=row["tokens_consumed"],
                created_at=row["created_at"]
            )
