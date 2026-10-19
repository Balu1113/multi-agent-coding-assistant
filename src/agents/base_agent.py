from __future__ import annotations

import abc
import uuid
import logging
from typing import TYPE_CHECKING, Any

from src.agents.models import AgentRole, Task, AgentResult

if TYPE_CHECKING:
    from src.communication.message_queue import MessageQueue

logger = logging.getLogger(__name__)


class BaseAgent(abc.ABC):
    def __init__(self, role: AgentRole, message_queue: MessageQueue) -> None:
        self.role = role
        self.id = f"{role.value}-{uuid.uuid4().hex[:6]}"
        self.message_queue = message_queue
        self._running = False

    @abc.abstractmethod
    async def execute_task(self, task: Task) -> AgentResult:
        ...

    async def delegate(
        self,
        target_role: AgentRole,
        task: Task,
        timeout: float = 60.0,
    ) -> AgentResult | None:
        logger.info(
            "%s delegating task %s to %s",
            self.role.value, task.id, target_role.value,
        )
        await self.message_queue.publish(target_role, task)
        return await self.message_queue.request_result(
            task.id, target_role, timeout=timeout,
        )

    async def run(self) -> None:
        self._running = True
        logger.info("Agent %s (%s) started", self.role.value, self.id)
        while self._running:
            task = await self.message_queue.consume(self.role)
            if task is None:
                continue
            logger.info("%s received task: %s", self.role.value, task.id)
            try:
                result = await self.execute_task(task)
                await self.message_queue.publish_result(task.id, self.role, result)
            except Exception as exc:
                logger.exception("%s failed on task %s", self.role.value, task.id)
                failed = AgentResult(
                    task_id=task.id,
                    agent_role=self.role,
                    success=False,
                    output=str(exc),
                )
                await self.message_queue.publish_result(task.id, self.role, failed)

    def stop(self) -> None:
        self._running = False
