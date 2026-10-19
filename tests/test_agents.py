import pytest
import asyncio
from src.agents.base_agent import AgentRole, Task, AgentResult
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
