"""Example: Run a full multi-agent coding workflow programmatically."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.orchestrator import AgentOrchestrator
from src.communication.message_queue import MessageQueue
from src.mcp.server import MCPServer, MCPRequest


async def run_workflow():
    print("=" * 60)
    print("Multi-Agent Coding Assistant — Example Workflow")
    print("=" * 60)

    # 1. Create the communication layer
    message_queue = MessageQueue()

    # 2. Create MCP server
    mcp = MCPServer()
    print("\n[1] MCP Server initialized")
    print(f"    Tools registered: {len(mcp.tools.list_all())}")
    print(f"    Resources available: {len(mcp.resources.list_all())}")

    # 3. Run a quick MCP tool call
    req = MCPRequest(
        method="tools/call",
        params={
            "name": "generate_code",
            "arguments": {"prompt": "hello world function", "language": "python"},
        },
    )
    resp = await mcp.handle_request(req)
    print(f"\n[2] MCP tool call result: {resp.result['content'][0]['text'][:80]}...")

    # 4. Run the orchestrator with a single request
    print("\n[3] Running agent workflow...")
    async with AgentOrchestrator(message_queue) as orchestrator:
        result = await orchestrator.process_request(
            "Write a function that calculates fibonacci numbers"
        )

    print("\n[4] Results:")
    print(f"    Code: {len(result.get('code', ''))} chars")
    print(f"    Review: {len(result.get('review', ''))} chars")
    print(f"    Tests: {len(result.get('tests', ''))} chars")
    print(f"    Artifacts: {result.get('artifacts', [])}")
    print("\n" + "=" * 60)
    print("Workflow complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_workflow())
