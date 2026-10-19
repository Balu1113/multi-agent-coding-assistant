import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from rich.console import Console
from rich.panel import Panel

from src.agents.orchestrator import AgentOrchestrator
from src.communication.message_queue import MessageQueue
from src.config import settings

logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)
console = Console()


async def main() -> None:
    console.print(Panel.fit(
        "[bold cyan]Multi-Agent Coding Assistant[/bold cyan]\n"
        "[dim]Coder • MCP • RAG • Fine-tuning • Evaluation[/dim]",
        border_style="cyan",
    ))

    message_queue = MessageQueue()

    async with AgentOrchestrator(message_queue) as orchestrator:
        await orchestrator.run_interactive_loop()


if __name__ == "__main__":
    asyncio.run(main())
