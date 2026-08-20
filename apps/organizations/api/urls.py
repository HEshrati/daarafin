from django.urls import path

from .summary import MasterDataSummaryView
from .views import (
    BankAccountListView,
    BranchListCreateView,
    ContactListCreateView,
    MasterDataImportView,
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
    path(
        "organizations/<int:pk>/contacts",
        ContactListCreateView.as_view(),
        name="organization-contacts",
    ),
    path(
        "organizations/<int:pk>/branches",
        BranchListCreateView.as_view(),
        name="organization-branches",
    ),
    path(
        "masterdata/import/<str:kind>",
        MasterDataImportView.as_view(),
        name="masterdata-import",
    ),
    path("masterdata/summary", MasterDataSummaryView.as_view(), name="masterdata-summary"),
]
