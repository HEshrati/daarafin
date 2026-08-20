from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.medicines import selectors, services
from apps.medicines.models import Medicine
from common.permissions import ensure_active_scope

from .serializers import MedicineInsurancePriceSerializer, MedicineSerializer


class MedicineListView(generics.ListAPIView):
    serializer_class = MedicineSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return selectors.medicines_for_list(search=self.request.query_params.get("search", ""))


class MedicineDetailView(generics.RetrieveAPIView):
    serializer_class = MedicineSerializer
    permission_classes = (IsAuthenticated,)
    queryset = Medicine.objects.all()


class MedicinePriceListView(generics.ListAPIView):
    serializer_class = MedicineInsurancePriceSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        medicine = generics.get_object_or_404(Medicine, pk=self.kwargs["pk"])
        return selectors.medicine_prices(medicine)


class MedicineImportView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        organization_id = request.data.get("organization_id") or (
            request.auth.get("organization_id")
            if request.auth and hasattr(request.auth, "get")
            else None
        )
        if not request.user.is_staff:
            if not organization_id:
                return Response(
                    {
                        "code": "organization_required",
                        "message": "شناسه سازمان برای بررسی دسترسی لازم است.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ensure_active_scope(
                user=request.user,
                organization_id=int(organization_id),
                scope="manage_medicines",
            )
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"code": "file_required", "message": "فایل اکسل الزامی است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(services.import_medicines_xlsx(file_bytes=upload.read()))


class InsurancePriceImportView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        organization_id = request.data.get("organization_id") or (
            request.auth.get("organization_id")
            if request.auth and hasattr(request.auth, "get")
            else None
        )
        if not request.user.is_staff:
            if not organization_id:
                return Response(
                    {
                        "code": "organization_required",
                        "message": "شناسه سازمان برای بررسی دسترسی لازم است.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ensure_active_scope(
                user=request.user,
                organization_id=int(organization_id),
                scope="manage_medicines",
            )
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"code": "file_required", "message": "فایل ODS/اکسل الزامی است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(services.import_insurance_prices_ods(file_bytes=upload.read()))
