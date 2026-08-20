from django.urls import path

from .views import (
    InsurancePriceImportView,
    MedicineDetailView,
    MedicineImportView,
    MedicineListView,
    MedicinePriceListView,
)

urlpatterns = [
    path("medicines", MedicineListView.as_view(), name="medicines"),
    path("medicines/import", MedicineImportView.as_view(), name="medicines-import"),
    path(
        "medicines/insurance-prices/import",
        InsurancePriceImportView.as_view(),
        name="insurance-prices-import",
    ),
    path("medicines/<int:pk>", MedicineDetailView.as_view(), name="medicine-detail"),
    path(
        "medicines/<int:pk>/prices",
        MedicinePriceListView.as_view(),
        name="medicine-prices",
    ),
]
