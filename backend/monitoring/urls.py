from django.urls import path
from monitoring import views

urlpatterns = [
    path("metrics/", views.MetricsView.as_view(), name="api-metrics"),
    path("benchmarks/", views.RunBenchmarksView.as_view(), name="api-benchmarks"),
]
