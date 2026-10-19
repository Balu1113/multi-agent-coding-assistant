"""FastAPI server — connects the React frontend to the multi-agent backend."""
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.agents.orchestrator import AgentOrchestrator
from src.communication.message_queue import MessageQueue
from src.config import settings

logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)

message_queue = MessageQueue()
orchestrator: AgentOrchestrator | None = None


class WorkflowRequest(BaseModel):
    prompt: str


class WorkflowResponse(BaseModel):
    success: bool
    code: str = ""
    review: str = ""
    tests: str = ""
    error: str = ""
    duration: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    orchestrator = AgentOrchestrator(message_queue)
    await orchestrator.__aenter__()
    logger.info("API server started with agent orchestrator")
    yield
    await orchestrator.__aexit__(None, None, None)
    logger.info("API server shut down")


app = FastAPI(
    title="Multi-Agent Coding Assistant API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "agents_running": len(orchestrator.agents) if orchestrator else 0,
    }


@app.post("/api/workflow", response_model=WorkflowResponse)
async def run_workflow(req: WorkflowRequest):
    if orchestrator is None:
        return WorkflowResponse(success=False, error="Orchestrator not initialized")

    start = time.perf_counter()
    try:
        result = await orchestrator.process_request(req.prompt)
        duration = time.perf_counter() - start

        if "error" in result:
            return WorkflowResponse(
                success=False,
                error=result["error"],
                duration=duration,
            )

        return WorkflowResponse(
            success=True,
            code=result.get("code", ""),
            review=result.get("review", ""),
            tests=result.get("tests", ""),
            duration=duration,
        )
    except Exception as exc:
        logger.exception("Workflow failed")
        return WorkflowResponse(
            success=False,
            error=str(exc),
            duration=time.perf_counter() - start,
        )


@app.get("/api/mcp/tools")
async def list_tools():
    from src.mcp.server import MCPServer
    server = MCPServer()
    return {"tools": [t.model_dump() for t in server.tools.list_all()]}


@app.get("/api/mcp/resources")
async def list_resources():
    from src.mcp.server import MCPServer
    server = MCPServer()
    return {"resources": server.resources.list_all()}


@app.post("/api/mcp/call")
async def call_tool(data: dict[str, Any]):
    from src.mcp.server import MCPServer
    server = MCPServer()
    from src.mcp.server import MCPRequest
    req = MCPRequest(
        method="tools/call",
        params={"name": data.get("name", ""), "arguments": data.get("arguments", {})},
    )
    resp = await server.handle_request(req)
    if resp.error:
        return {"error": resp.error["message"]}
    return {"result": resp.result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api_server:app", host="0.0.0.0", port=8000, reload=True)
