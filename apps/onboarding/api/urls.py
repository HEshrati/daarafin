from django.urls import path

from .views import CaseListCreateView, DecisionView, SubmitView

urlpatterns = [
    path("onboarding/cases/", CaseListCreateView.as_view()),
    path("onboarding/<int:pk>/submit", SubmitView.as_view()),
    path("onboarding/<int:pk>/decision", DecisionView.as_view()),
]
