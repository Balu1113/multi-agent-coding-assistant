from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncIterator

from src.agents.base_agent import AgentRole, Task
from src.agents.coder_agent import CoderAgent
from src.agents.planning_agent import PlanningAgent
from src.agents.research_agent import ResearchAgent
from src.communication.message_queue import MessageQueue
from src.rag.retriever import RAGRetriever
from src.evaluation.monitor import Monitor

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self, message_queue: MessageQueue) -> None:
        self.message_queue = message_queue
        self.agents: list = []
        self.monitor = Monitor()

    async def __aenter__(self) -> AgentOrchestrator:
        retriever = RAGRetriever()

        self.agents = [
            CoderAgent(self.message_queue, retriever),
            PlanningAgent(self.message_queue, retriever),
            ResearchAgent(self.message_queue, retriever),
        ]
        for agent in self.agents:
            asyncio.create_task(agent.run())
        logger.info("Orchestrator started with %d agents", len(self.agents))
        return self

    async def __aexit__(self, *args: object) -> None:
        for agent in self.agents:
            agent.stop()
        logger.info("Orchestrator stopped")

    async def run_interactive_loop(self) -> None:
        from rich.prompt import Prompt

        print("\nEnter a coding task (or 'quit' to exit):")
        while True:
            user_input = Prompt.ask("[bold green]>>[/bold green]")
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if not user_input.strip():
                continue

            result = await self.process_request(user_input)
            self._show_result(result)

    async def process_request(
        self,
        prompt: str,
        history: list | None = None,
        agents: list | None = None,
        service: str = "",
        plan: str | None = None,
        execute_plan: bool = False,
        plan_approved: bool = False,
        research_mode: bool = False,
    ) -> dict:
        self.monitor.record_request()

        agent_filter = agents if agents else []
        run_planner = "planner" in agent_filter
        run_researcher = "researcher" in agent_filter or research_mode
        run_coder = "coder" in agent_filter or not agent_filter

        task = Task(
            description=prompt,
            context={"source": "user", "prompt": prompt, "history": history or []},
        )

        if run_researcher:
            researcher = self._get_agent(AgentRole.RESEARCHER)
            research_result = await researcher.delegate(AgentRole.RESEARCHER, task)
            if research_result and research_result.success:
                return {
                    "type": "research",
                    "research": research_result.output,
                    "artifacts": research_result.artifacts,
                }

        if run_planner and not plan_approved:
            planner = self._get_agent(AgentRole.PLANNER)
            plan_result = await planner.delegate(AgentRole.PLANNER, task)
            if plan_result and plan_result.success:
                return {
                    "type": "plan",
                    "plan": plan_result.output,
                    "requires_approval": True,
                }

        code = ""
        review = ""
        tests = ""

        if run_coder:
            coder_task = Task(
                description=prompt,
                context={
                    "source": "user",
                    "prompt": prompt,
                    "history": history or [],
                    "plan": plan or "",
                },
            )
            coder_agent = self._get_agent(AgentRole.CODER)
            coder_result = await coder_agent.delegate(AgentRole.CODER, coder_task)
            if coder_result and coder_result.success:
                code = coder_result.metadata.get("code", "")
                review = coder_result.metadata.get("review", "")
                tests = coder_result.metadata.get("tests", "")
            else:
                error = coder_result.output if coder_result else "Coder failed"
                return {"error": error, "type": "error"}

        final = {
            "type": "code",
            "code": code,
            "review": review,
            "tests": tests,
            "artifacts": [],
        }
        self.monitor.record_success()
        return final

    def _get_agent(self, role: AgentRole):
        for agent in self.agents:
            if agent.role == role:
                return agent
        raise ValueError(f"No agent found for role {role}")

    def _has_agent(self, role: AgentRole) -> bool:
        return any(agent.role == role for agent in self.agents)

    def _show_result(self, result: dict) -> None:
        from rich.syntax import Syntax
        from rich.panel import Panel
        from rich.console import Console

        console = Console()
        if result.get("type") == "plan":
            console.print(Panel(result.get("plan", ""), title="[cyan]Implementation Plan[/cyan]", border_style="cyan"))
            return
        if "error" in result:
            console.print(Panel(f"[red]{result['error']}[/red]", title="Error"))
            return

        console.print(Panel(
            Syntax(result.get("code", ""), "python", theme="monokai"),
            title="[green]Generated Code[/green]",
            border_style="green",
        ))
        if result.get("review"):
            console.print(Panel(result["review"], title="[yellow]Review[/yellow]", border_style="yellow"))
        if result.get("tests"):
            console.print(Panel(
                Syntax(result["tests"], "python", theme="monokai"),
                title="[blue]Tests[/blue]",
                border_style="blue",
            ))
