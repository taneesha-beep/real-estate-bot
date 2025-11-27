from django.urls import path
from .views import AnalyzeAPIView, DownloadDataAPIView

urlpatterns = [
    path("analyze/", AnalyzeAPIView.as_view(), name="analyze"),
    path("download/", DownloadDataAPIView.as_view(), name="download"),
]