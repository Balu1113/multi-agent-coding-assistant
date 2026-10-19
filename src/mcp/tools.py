from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., Coroutine[Any, Any, str]]


class ToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolDefinition, ToolHandler]] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: ToolHandler,
        schema: dict[str, Any] | None = None,
    ) -> None:
        definition = ToolDefinition(
            name=name,
            description=description,
            inputSchema=schema or {"type": "object", "properties": {}},
        )
        self._tools[name] = (definition, handler)
        logger.info("MCP tool registered: %s", name)

    def list_all(self) -> list[ToolDefinition]:
        return [defn for defn, _ in self._tools.values()]

    async def call(self, name: str, arguments: dict[str, Any]) -> str:
        entry = self._tools.get(name)
        if entry is None:
            raise ValueError(f"Unknown tool: {name}")
        _, handler = entry
        return await handler(**arguments)


class CodingTools:
    @staticmethod
    async def generate_code(
        prompt: str,
        language: str = "python",
        style: str = "standard",
    ) -> str:
        return (
            f"def generated_function():\n"
            f'    """Generated based on: {prompt}"""\n'
            f"    pass\n"
        )

    @staticmethod
    async def explain_code(code: str, detail: str = "high") -> str:
        lines = code.strip().split("\n")
        return (
            f"## Code Explanation ({detail} detail)\n\n"
            f"The code has {len(lines)} lines.\n"
            f"```\n{code[:500]}\n```\n"
        )

    @staticmethod
    async def search_docs(query: str, top_k: int = 3) -> str:
        return f"Search results for '{query}' (top {top_k}):\n- Placeholder result 1\n- Placeholder result 2"

    @staticmethod
    async def format_code(code: str, style: str = "black") -> str:
        return code.strip()

    @staticmethod
    async def analyze_complexity(code: str) -> str:
        return (
            "## Complexity Analysis\n\n"
            "- Lines of code: {}\n"
            "- Estimated cyclomatic complexity: Low\n"
            "- Recommended improvements: None detected"
        ).format(len(code.strip().split("\n")))
