import subprocess
import time
import os
from typing import Dict, Any
from .models import ToolResult


class SubprocessSandbox:
    """
    Isolates tool execution (python, bash scripts, git) within a designated workspace.
    Enforces timeout boundaries and output truncation to prevent context poisoning.
    """

    def __init__(self, workspace_dir: str = "./sandbox_workspace", default_timeout_sec: int = 30):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.default_timeout_sec = default_timeout_sec
        os.makedirs(self.workspace_dir, exist_ok=True)

    def execute_command(self, command: str, timeout_sec: int | None = None) -> ToolResult:
        start_time = time.time()
        timeout = timeout_sec or self.default_timeout_sec

        try:
            process = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            duration_ms = (time.time() - start_time) * 1000

            output = process.stdout
            if process.stderr:
                output += ("\n[STDERR]\n" + process.stderr)

            # Truncate overly verbose outputs to prevent context window explosion
            if len(output) > 8000:
                output = output[:8000] + "\n...[TRUNCATED: Output exceeded 8000 characters]"

            is_error = process.returncode != 0
            return ToolResult(
                tool_name="bash_execute",
                output=output if output.strip() else "[Command executed with no output]",
                is_error=is_error,
                duration_ms=round(duration_ms, 2)
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.time() - start_time) * 1000
            return ToolResult(
                tool_name="bash_execute",
                output=f"[TIMEOUT ERROR]: Command exceeded execution limit of {timeout}s",
                is_error=True,
                duration_ms=round(duration_ms, 2)
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ToolResult(
                tool_name="bash_execute",
                output=f"[EXECUTION ERROR]: {str(e)}",
                is_error=True,
                duration_ms=round(duration_ms, 2)
            )

    def write_file(self, relative_path: str, content: str) -> ToolResult:
        full_path = os.path.join(self.workspace_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(
                tool_name="write_file",
                output=f"Successfully written {len(content)} bytes to {relative_path}",
                is_error=False
            )
        except Exception as e:
            return ToolResult(
                tool_name="write_file",
                output=f"[FILE WRITE ERROR]: {str(e)}",
                is_error=True
            )

    def read_file(self, relative_path: str) -> ToolResult:
        full_path = os.path.join(self.workspace_dir, relative_path)
        if not os.path.exists(full_path):
            return ToolResult(
                tool_name="read_file",
                output=f"[NOT FOUND]: File {relative_path} does not exist.",
                is_error=True
            )
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            return ToolResult(
                tool_name="read_file",
                output=content,
                is_error=False
            )
        except Exception as e:
            return ToolResult(
                tool_name="read_file",
                output=f"[FILE READ ERROR]: {str(e)}",
                is_error=True
            )
