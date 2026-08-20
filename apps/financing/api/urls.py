from django.urls import path

from .views import (
    ApproveView,
    DisburseView,
    QuoteCreateView,
    RejectView,
    RequestDetailView,
    RequestListCreateView,
)

urlpatterns = [
    path("financing/quotes", QuoteCreateView.as_view()),
    path("financing/requests", RequestListCreateView.as_view()),
    path("financing/<int:pk>", RequestDetailView.as_view()),
    path("financing/<int:pk>/approve", ApproveView.as_view()),
    path("financing/<int:pk>/reject", RejectView.as_view()),
    path("financing/<int:pk>/disburse", DisburseView.as_view()),
]
