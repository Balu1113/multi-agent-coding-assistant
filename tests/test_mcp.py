import pytest
from src.mcp.server import MCPServer, MCPRequest


@pytest.mark.asyncio
async def test_mcp_initialize():
    server = MCPServer()
    req = MCPRequest(method="initialize", id=1)
    resp = await server.handle_request(req)
    assert resp.result is not None
    assert resp.result["protocolVersion"] == "2024-11-05"
    assert "tools" in resp.result["capabilities"]


@pytest.mark.asyncio
async def test_mcp_tools_list():
    server = MCPServer()
    req = MCPRequest(method="tools/list", id=2)
    resp = await server.handle_request(req)
    assert resp.result is not None
    assert "tools" in resp.result
    assert len(resp.result["tools"]) > 0


@pytest.mark.asyncio
async def test_mcp_tools_call():
    server = MCPServer()
    req = MCPRequest(
        method="tools/call",
        params={"name": "generate_code", "arguments": {"prompt": "hello", "language": "python"}},
        id=3,
    )
    resp = await server.handle_request(req)
    assert resp.result is not None
    assert len(resp.result["content"]) > 0


@pytest.mark.asyncio
async def test_mcp_resources_list():
    server = MCPServer()
    req = MCPRequest(method="resources/list", id=4)
    resp = await server.handle_request(req)
    assert resp.result is not None
    assert len(resp.result["resources"]) > 0


@pytest.mark.asyncio
async def test_mcp_unknown_method():
    server = MCPServer()
    req = MCPRequest(method="unknown", id=5)
    resp = await server.handle_request(req)
    assert resp.error is not None
    assert resp.error["code"] == -32601
