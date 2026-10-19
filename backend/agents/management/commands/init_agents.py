import os
import sys
import asyncio
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Initialize and verify the agent orchestrator"

    def handle(self, *args, **options):
        from src.communication.message_queue import MessageQueue
        from src.agents.orchestrator import AgentOrchestrator

        self.stdout.write("Initializing agent orchestrator...")

        message_queue = MessageQueue()

        async def init():
            async with AgentOrchestrator(message_queue) as orch:
                agent_count = len(orch.agents)
                self.stdout.write(self.style.SUCCESS(
                    f"Orchestrator running with {agent_count} agents "
                    f"({', '.join(a.role.value for a in orch.agents)})"
                ))
                return orch

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(init())
        loop.close()
