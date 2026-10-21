import pytest
import asyncio
from src.agents.base_agent import AgentRole, Task, AgentResult
from src.agents.coder_agent import CoderAgent, _format_history
from src.communication.message_queue import MessageQueue


@pytest.mark.asyncio
async def test_message_queue_publish_consume():
    q = MessageQueue()
    task = Task(description="test task")
    await q.publish(AgentRole.CODER, task)
    consumed = await q.consume(AgentRole.CODER)
    assert consumed is not None
    assert consumed.id == task.id
    assert consumed.description == "test task"


@pytest.mark.asyncio
async def test_message_queue_result():
    q = MessageQueue()
    task = Task(description="test")
    result = AgentResult(task_id=task.id, agent_role=AgentRole.CODER, success=True, output="ok")
    await q.publish(AgentRole.CODER, task)

    async def publish_later():
        await asyncio.sleep(0.05)
        await q.publish_result(task.id, AgentRole.CODER, result)

    asyncio.create_task(publish_later())
    received = await q.request_result(task.id, AgentRole.CODER, timeout=2.0)
    assert received is not None
    assert received.output == "ok"


@pytest.mark.asyncio
async def test_message_queue_timeout():
    q = MessageQueue()
    task = Task(description="timeout task")
    result = await q.request_result(task.id, AgentRole.CODER, timeout=0.1)
    assert result is None


def test_task_model_defaults():
    task = Task(description="hello")
    assert task.status == "pending"
    assert task.dependencies == []
    assert task.context == {}


def test_agent_role_values():
    assert AgentRole.CODER.value == "coder"
    assert AgentRole.PLANNER.value == "planner"
    assert AgentRole.RESEARCHER.value == "researcher"


def test_workspace_context_is_included_in_coder_history():
    history = [{
        "prompt": "Workspace context",
        "result": {
            "type": "workspace_context",
            "files": [{"path": "src/example.py", "content": "def answer(): return 42"}],
        },
    }]

    formatted = _format_history(history)

    assert "src/example.py" in formatted
    assert "def answer(): return 42" in formatted


def test_workspace_context_bounds_large_file_and_marks_truncation():
    content = "x" * 500000
    formatted = _format_history([{
        "prompt": "Workspace context",
        "result": {
            "type": "workspace_context",
            "files": [{"path": "src/large_module.py", "content": content}],
        },
    }])

    assert content[:1000] in formatted
    assert content not in formatted
    assert "[File content truncated to fit model context]" in formatted


@pytest.mark.asyncio
async def test_coder_surfaces_model_failure_instead_of_returning_placeholder(monkeypatch):
    async def fail_to_thread(_function):
        raise PermissionError("provider rejected credentials")

    monkeypatch.setattr("src.agents.coder_agent.asyncio.to_thread", fail_to_thread)
    agent = object.__new__(CoderAgent)

    with pytest.raises(RuntimeError, match="configured model request failed"):
        await agent._write_code("implement a function", [], "")
