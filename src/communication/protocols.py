from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    REQUEST_REVIEW = "request_review"
    REQUEST_TEST = "request_test"
    STATUS_UPDATE = "status_update"
    ERROR = "error"


class Message(BaseModel):
    type: MessageType
    sender: str
    recipient: str
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
