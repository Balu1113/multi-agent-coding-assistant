from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from typing import Any

from src.agents.models import AgentRole, Task, AgentResult

logger = logging.getLogger(__name__)


class MessageQueue:
    def __init__(self) -> None:
        self._queues: dict[AgentRole, asyncio.Queue[Task | None]] = defaultdict(asyncio.Queue)
        self._results: dict[str, asyncio.Future[AgentResult]] = {}

    async def publish(self, role: AgentRole, task: Task) -> None:
        await self._queues[role].put(task)
        logger.debug("Task %s published to %s", task.id, role.value)

    async def consume(self, role: AgentRole) -> Task | None:
        try:
            return await asyncio.wait_for(self._queues[role].get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    async def publish_result(self, task_id: str, role: AgentRole, result: AgentResult) -> None:
        key = f"{task_id}:{role.value}"
        future = self._results.get(key)
        if future is not None and not future.done():
            future.set_result(result)
        logger.debug("Result for task %s from %s published", task_id, role.value)

    async def request_result(
        self,
        task_id: str,
        role: AgentRole,
        timeout: float = 60.0,
    ) -> AgentResult | None:
        key = f"{task_id}:{role.value}"
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._results[key] = future
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for result on task %s from %s", task_id, role.value)
            return None
        finally:
            self._results.pop(key, None)
