from django.urls import path

from .views import (
    BulkCommitView,
    BulkPreviewView,
    DisputeView,
    InvoiceDetailView,
    InvoiceListCreateView,
    VerifyView,
)

urlpatterns = [
    path("invoices", InvoiceListCreateView.as_view()),
    path("invoices/<int:pk>", InvoiceDetailView.as_view()),
    path("invoices/<int:pk>/verify", VerifyView.as_view()),
    path("invoices/<int:pk>/dispute", DisputeView.as_view()),
    path("invoices/bulk-commit", BulkCommitView.as_view()),
    path("invoices/bulk-preview", BulkPreviewView.as_view()),
]
