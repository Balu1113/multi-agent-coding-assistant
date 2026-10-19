from __future__ import annotations

import logging
import uuid
from src.agents.base_agent import BaseAgent, AgentRole, AgentResult, Task
from src.communication.message_queue import MessageQueue

logger = logging.getLogger(__name__)


class PlanningAgent(BaseAgent):
    def __init__(self, message_queue: MessageQueue, retriever=None) -> None:
        super().__init__(AgentRole.PLANNER, message_queue)
        self.role = AgentRole.PLANNER
        self.id = f"planner-{uuid.uuid4().hex[:6]}"

    async def execute_task(self, task: Task) -> AgentResult:
        prompt = task.description
        history = task.context.get("history", [])

        from src.llm_service import chat_with_llm

        system_context = ""
        if history:
            system_context = "Previous conversation:\n" + "\n".join(
                f"User: {h.get('prompt', '')}\nAssistant: {h.get('result', {}).get('message', '')}"
                for h in history[-6:]
            ) + "\n\n"

        plan_prompt = (
            "You are an expert software architect. Create a detailed implementation plan "
            "for the following coding request. Break it down into clear steps. "
            "For each step, specify what files to create/modify, what functions/classes to implement, "
            "and how they interact. Be specific and actionable.\n\n"
            f"Request: {prompt}"
        )

        full_prompt = f"{system_context}{plan_prompt}"
        plan = chat_with_llm(full_prompt)

        return AgentResult(
            task_id=task.id,
            agent_role=self.role,
            success=True,
            output=plan,
            artifacts=[{"type": "plan", "content": plan}],
        )

        full_prompt = f"{system_context}{plan_prompt}"
        plan = chat_with_llm(full_prompt)

        return AgentResult(
            success=True,
            output=plan,
            artifacts=[{"type": "plan", "content": plan}],
        )
