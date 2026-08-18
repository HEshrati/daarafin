from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import MeView, SessionsView

urlpatterns = [
    path("auth/token", TokenObtainPairView.as_view(), name="token"),
    path("auth/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("me", MeView.as_view(), name="me"),
    path("sessions", SessionsView.as_view(), name="sessions"),
]
