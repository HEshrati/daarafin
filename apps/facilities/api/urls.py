from django.urls import path

from .views import FacilityDetailView, FacilityListCreateView, HistoryView, ReserveView

urlpatterns = [
    path("facilities", FacilityListCreateView.as_view()),
    path("facilities/<int:pk>", FacilityDetailView.as_view()),
    path("facilities/<int:pk>/reserve", ReserveView.as_view()),
    path("facilities/<int:pk>/history", HistoryView.as_view()),
    path("facilities/<int:pk>/limits", FacilityDetailView.as_view()),
    path("facilities/<int:pk>/utilization", FacilityDetailView.as_view()),
]
