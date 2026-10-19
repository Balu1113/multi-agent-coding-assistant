from __future__ import annotations

from typing import Any


class ResourceManager:
    def __init__(self) -> None:
        self._resources: dict[str, str] = {
            "docs://architecture": (
                "# Architecture\n\n"
                "The Multi-Agent Coding Assistant uses three specialized agents:\n"
                "- **Writer**: Generates code\n"
                "- **Reviewer**: Reviews code quality\n"
                "- **Tester**: Creates and runs tests\n\n"
                "Agents communicate via a message queue and can delegate tasks.\n"
                "MCP provides tool and resource access. RAG enables document retrieval."
            ),
            "docs://agents": (
                "# Agent System\n\n"
                "Each agent runs as an async loop, consuming tasks from a shared message queue.\n"
                "Agents can delegate subtasks to other agents using `agent.delegate()`.\n"
                "Results are published back to the queue for the orchestrator to collect."
            ),
            "docs://mcp": (
                "# Model Context Protocol\n\n"
                "MCP is an open standard for connecting AI models to tools and data.\n"
                "Supported methods: initialize, tools/list, tools/call, resources/list, resources/read."
            ),
            "config://defaults": (
                '{\n'
                '  "llm_provider": "openai",\n'
                '  "model": "gpt-4o",\n'
                '  "rag_enabled": true,\n'
                '  "max_iterations": 3\n'
                '}'
            ),
        }

    def list_all(self) -> list[dict[str, Any]]:
        return [
            {"uri": uri, "name": uri.split("://")[1], "description": text[:80]}
            for uri, text in self._resources.items()
        ]

    def read(self, uri: str) -> str | None:
        return self._resources.get(uri)

    def register(self, uri: str, content: str) -> None:
        self._resources[uri] = content
