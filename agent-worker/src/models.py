from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
import datetime


class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    idempotency_key: str = Field(description="Unique key to prevent duplicate execution upon retry")


class ToolResult(BaseModel):
    tool_name: str
    output: str
    is_error: bool = False
    duration_ms: float = 0.0


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_result: Optional[ToolResult] = None


class CheckpointData(BaseModel):
    task_id: str
    turn_index: int
    status: Literal["RUNNING", "REQUIRES_APPROVAL", "COMPLETED", "FAILED"]
    messages: List[Message]
    scratchpad: Dict[str, Any] = Field(default_factory=dict)
    disk_diff_summary: Optional[str] = None
    tokens_consumed: int = 0
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class InboundTaskPayload(BaseModel):
    id: str
    title: str
    description: str
    metadataJson: Optional[str] = None
