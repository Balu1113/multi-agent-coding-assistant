from django.urls import path
from mcp import views

urlpatterns = [
    path("tools/", views.ListToolsView.as_view(), name="mcp-tools"),
    path("resources/", views.ListResourcesView.as_view(), name="mcp-resources"),
    path("call/", views.CallToolView.as_view(), name="mcp-call"),
]
