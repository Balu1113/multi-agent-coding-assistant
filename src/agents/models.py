from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    CODER = "coder"
    PLANNER = "planner"
    RESEARCHER = "researcher"
    ORCHESTRATOR = "orchestrator"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str
    context: dict[str, Any] = Field(default_factory=dict)
    assigned_to: AgentRole | None = None
    dependencies: list[str] = Field(default_factory=list)
    status: str = "pending"
    result: dict[str, Any] | None = None
    artifacts: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    task_id: str
    agent_role: AgentRole
    success: bool
    output: str
    artifacts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
