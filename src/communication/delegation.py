from __future__ import annotations

import logging

from src.agents.models import AgentRole

logger = logging.getLogger(__name__)


class DelegationManager:
    def __init__(self) -> None:
        self._capability_map: dict[str, AgentRole] = {
            "write_code": AgentRole.CODER,
            "implement": AgentRole.CODER,
            "review": AgentRole.CODER,
            "test": AgentRole.CODER,
        }

    def resolve_role(self, task_description: str) -> AgentRole | None:
        desc_lower = task_description.lower()
        for keyword, role in self._capability_map.items():
            if keyword in desc_lower:
                return role
        return None

    def register_capability(self, keyword: str, role: AgentRole) -> None:
        self._capability_map[keyword] = role
