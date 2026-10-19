"""Model Context Protocol (MCP) Server.

MCP provides a standardized way for LLMs to interact with tools and data sources.
This implementation follows the MCP specification used by OpenAI, Anthropic, and Google.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from src.mcp.tools import ToolRegistry, CodingTools
from src.mcp.resources import ResourceManager

logger = logging.getLogger(__name__)


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict[str, Any] = Field(default_factory=dict)
    id: str | int | None = None


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    id: str | int | None = None


class MCPServer:
    """Core MCP server that registers tools/resources and handles requests."""

    def __init__(self) -> None:
        self.tools = ToolRegistry()
        self.resources = ResourceManager()
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        ct = CodingTools()
        self.tools.register(
            "generate_code", "Generate code from a prompt", ct.generate_code,
            schema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Description of the code to generate"},
                    "language": {"type": "string", "description": "Programming language"},
                    "style": {"type": "string", "description": "Code style"},
                },
                "required": ["prompt"],
            },
        )
        self.tools.register(
            "explain_code", "Explain what code does", ct.explain_code,
            schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to explain"},
                    "detail": {"type": "string", "description": "Detail level: high or low"},
                },
                "required": ["code"],
            },
        )
        self.tools.register(
            "search_docs", "Search documentation", ct.search_docs,
            schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "description": "Number of results"},
                },
                "required": ["query"],
            },
        )
        self.tools.register(
            "format_code", "Format code to follow style conventions", ct.format_code,
        )
        self.tools.register(
            "analyze_complexity", "Analyze code complexity", ct.analyze_complexity,
        )

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        method = request.method

        if method == "tools/list":
            return MCPResponse(
                result={"tools": [t.model_dump() for t in self.tools.list_all()]},
                id=request.id,
            )
        elif method == "tools/call":
            return await self._handle_tool_call(request)
        elif method == "resources/list":
            return MCPResponse(
                result={"resources": self.resources.list_all()},
                id=request.id,
            )
        elif method == "resources/read":
            return await self._handle_resource_read(request)
        elif method == "initialize":
            return MCPResponse(
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                    },
                    "serverInfo": {
                        "name": "multi-agent-coding-assistant",
                        "version": "0.1.0",
                    },
                },
                id=request.id,
            )
        else:
            return MCPResponse(
                error={"code": -32601, "message": f"Method not found: {method}"},
                id=request.id,
            )

    async def _handle_tool_call(self, request: MCPRequest) -> MCPResponse:
        tool_name = request.params.get("name", "")
        arguments = request.params.get("arguments", {})

        try:
            result = await self.tools.call(tool_name, arguments)
            return MCPResponse(result={"content": [{"type": "text", "text": result}]}, id=request.id)
        except ValueError as exc:
            return MCPResponse(
                error={"code": -32602, "message": str(exc)},
                id=request.id,
            )

    async def _handle_resource_read(self, request: MCPRequest) -> MCPResponse:
        uri = request.params.get("uri", "")
        content = self.resources.read(uri)
        if content is None:
            return MCPResponse(
                error={"code": -32602, "message": f"Resource not found: {uri}"},
                id=request.id,
            )
        return MCPResponse(
            result={"contents": [{"uri": uri, "text": content}]},
            id=request.id,
        )
