from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    name: str
    provider: str
    version: str
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, ModelInfo] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(ModelInfo(
            name="gpt-4o",
            provider="openai",
            version="2024-08-06",
            capabilities=["code_generation", "review", "explain", "debug"],
        ))
        self.register(ModelInfo(
            name="claude-3-opus",
            provider="anthropic",
            version="2024-10-01",
            capabilities=["code_generation", "review", "architect"],
        ))
        self.register(ModelInfo(
            name="codellama-7b",
            provider="huggingface",
            version="1.0",
            capabilities=["code_generation", "completion"],
        ))

    def register(self, info: ModelInfo) -> None:
        self._models[info.name] = info
        logger.info("Registered model: %s (%s)", info.name, info.provider)

    def get(self, name: str) -> ModelInfo | None:
        return self._models.get(name)

    def list_by_capability(self, capability: str) -> list[ModelInfo]:
        return [m for m in self._models.values() if capability in m.capabilities]

    def list_all(self) -> dict[str, ModelInfo]:
        return dict(self._models)

    async def select_for_task(self, task: str, preferred: str | None = None) -> ModelInfo | None:
        if preferred and preferred in self._models:
            return self._models[preferred]
        task_lower = task.lower()
        if "test" in task_lower:
            return self._models.get("gpt-4o")
        if "review" in task_lower:
            return self._models.get("claude-3-opus")
        return self._models.get("gpt-4o")
