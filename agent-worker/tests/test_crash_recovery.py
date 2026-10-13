import os
import shutil
import pytest
from src.models import CheckpointData, Message
from src.checkpoint import CheckpointStore
from src.sandbox import SubprocessSandbox
from src.agent_loop import DurableAgentLoop


@pytest.fixture
def clean_env():
    test_dir = "./tests/data"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)

    test_db = os.path.join(test_dir, "test_checkpoints.db")
    test_sandbox = os.path.join(test_dir, "sandbox")
    os.makedirs(os.path.dirname(test_db), exist_ok=True)
    os.makedirs(test_sandbox, exist_ok=True)

    yield test_db, test_sandbox

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)


def test_crash_recovery_resumes_from_exact_checkpoint(clean_env):
    test_db, test_sandbox = clean_env

    store = CheckpointStore(db_path=test_db)
    sandbox = SubprocessSandbox(workspace_dir=test_sandbox)

    task_id = "test-task-crash-resilience-42"
    instruction = "Create a solution script and verify its execution."

    # Phase 1: Simulate Agent running Turn 1 & Turn 2, then crashing
    loop_instance_1 = DurableAgentLoop(checkpoint_store=store, sandbox=sandbox, max_turns=2)
    partial_result = loop_instance_1.execute(task_id, instruction)

    # Verify that partial run checkpointed at Turn 2
    assert partial_result.turn_index == 2
    assert os.path.exists(os.path.join(test_sandbox, "solution.py"))

    # Phase 2: Simulate Worker restart after crash
    # A completely new instance is initialized with the same persistent store
    loop_instance_2 = DurableAgentLoop(checkpoint_store=store, sandbox=sandbox, max_turns=15)
    resumed_result = loop_instance_2.execute(task_id, instruction)

    # Assert that it resumed from Turn 3 and completed without re-running turn 1 or 2
    assert resumed_result.status == "COMPLETED"
    assert resumed_result.turn_index == 4  # Turn 3 executed python, Turn 4 completed
    
    # Check that solution.py is still present and valid
    with open(os.path.join(test_sandbox, "solution.py"), "r") as f:
        content = f.read()
    assert "Hello from Agent!" in content
