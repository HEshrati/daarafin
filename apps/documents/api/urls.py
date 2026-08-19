from django.urls import path

from .views import CompleteView, DownloadUrlView, PresignView

urlpatterns = [
    path("documents/presign", PresignView.as_view()),
    path("documents/<int:pk>/complete", CompleteView.as_view()),
    path("documents/<int:pk>/download-url", DownloadUrlView.as_view()),
]
