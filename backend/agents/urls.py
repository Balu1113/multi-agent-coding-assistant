from django.urls import path
from agents import views

urlpatterns = [
    path("health/", views.HealthView.as_view(), name="api-health"),
    path("workflow/", views.WorkflowView.as_view(), name="api-workflow"),
    path("workspace-agent/", views.WorkspaceAgentView.as_view(), name="api-workspace-agent"),
    path("chat/", views.ChatView.as_view(), name="api-chat"),
    path("debug/", views.DebugView.as_view(), name="api-debug"),
    path("languages/", views.LanguagesView.as_view(), name="api-languages"),
    path("models/", views.ModelsView.as_view(), name="api-models"),
    path("git-proxy/<path:remote_path>", views.GitProxyView.as_view(), name="api-git-proxy"),
    path("upload/", views.UploadFileView.as_view(), name="api-upload"),
    path("image/", views.GenerateImageView.as_view(), name="api-image"),
    path("approve-plan/", views.ApprovePlanView.as_view(), name="api-approve-plan"),
    path("usage/", views.UsageStatsView.as_view(), name="api-usage"),

]
