from django.urls import path

from .views import MeView, SessionsView, ThrottledTokenObtainPairView, ThrottledTokenRefreshView

urlpatterns = [
    path("auth/token", ThrottledTokenObtainPairView.as_view(), name="token"),
    path("auth/refresh", ThrottledTokenRefreshView.as_view(), name="token-refresh"),
    path("me", MeView.as_view(), name="me"),
    path("sessions", SessionsView.as_view(), name="sessions"),
]
