from django.urls import path

from .views import (
    BankAccountListView,
    MemberListCreateView,
    OrganizationDetailView,
    OrganizationListCreateView,
)

urlpatterns = [
    path("organizations", OrganizationListCreateView.as_view(), name="organizations"),
    path("organizations/<int:pk>", OrganizationDetailView.as_view(), name="organization-detail"),
    path(
        "organizations/<int:pk>/members",
        MemberListCreateView.as_view(),
        name="organization-members",
    ),
    path(
        "organizations/<int:pk>/bank-accounts",
        BankAccountListView.as_view(),
        name="organization-bank-accounts",
    ),
]
