from django.http import JsonResponse
from django.urls import path, include


def api_root(request):
    return JsonResponse({
        "service": "Multi-Agent Coding Assistant API",
        "version": "0.1.0",
        "endpoints": {
            "health": "/api/health/",
            "workflow": "/api/workflow/",
            "mcp_tools": "/api/mcp/tools/",
            "mcp_resources": "/api/mcp/resources/",
            "mcp_call": "/api/mcp/call/",
            "metrics": "/api/metrics/",
            "benchmarks": "/api/benchmarks/",
        },
    })


urlpatterns = [
    path("", api_root, name="api-root"),
    path("api/", include("agents.urls")),
    path("api/mcp/", include("mcp.urls")),
    path("api/", include("monitoring.urls")),
]
