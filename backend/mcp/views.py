import os
import sys
from pathlib import Path

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.serializers import MCPCallInputSerializer


def _get_mcp_server():
    from src.mcp.server import MCPServer

    return MCPServer()


class ListToolsView(APIView):
    def get(self, request: Request):
        server = _get_mcp_server()
        tools = [t.model_dump() for t in server.tools.list_all()]
        return Response({"tools": tools})


class ListResourcesView(APIView):
    def get(self, request: Request):
        server = _get_mcp_server()
        resources = server.resources.list_all()
        return Response({"resources": resources})


class CallToolView(APIView):
    def post(self, request: Request):
        serializer = MCPCallInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        from src.mcp.server import MCPRequest

        server = _get_mcp_server()

        req = MCPRequest(
            method="tools/call",
            params={
                "name": serializer.validated_data["name"],
                "arguments": serializer.validated_data.get("arguments", {}),
            },
        )

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        resp = loop.run_until_complete(server.handle_request(req))
        loop.close()

        if resp.error:
            return Response({"error": resp.error["message"]}, status=400)
        return Response({"result": resp.result})

