from rest_framework import generics
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Document
from apps.invoices import services
from apps.invoices.models import Invoice
from apps.organizations.models import UserMembership
from common.errors import DomainError

from .serializers import BulkSerializer, DisputeSerializer, InvoiceSerializer


class InvoicePagination(CursorPagination):
    ordering = "-created_at"


class InvoiceListCreateView(generics.ListCreateAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = InvoicePagination

    def get_queryset(self):
        qs = Invoice.objects.filter(
            issuer__memberships__user=self.request.user
        ) | Invoice.objects.filter(buyer__memberships__user=self.request.user)
        for field in ("status", "buyer", "due_date"):
            if value := self.request.query_params.get(field):
                qs = qs.filter(**{field: value})
        return qs.distinct()

    def perform_create(self, s):
        if not UserMembership.objects.filter(
            user=self.request.user,
            organization=s.validated_data["issuer"],
            is_active=True,
        ).exists():
            raise DomainError(
                "forbidden_issuer",
                "اجازه صدور فاکتور برای این سازمان را ندارید.",
                status_code=403,
            )
        s.instance = services.create_invoice(
            actor=self.request.user,
            data=s.validated_data,
            correlation_id=getattr(self.request, "correlation_id", ""),
        )


class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return (
            Invoice.objects.filter(issuer__memberships__user=self.request.user)
            | Invoice.objects.filter(buyer__memberships__user=self.request.user)
        ).distinct()

    def perform_update(self, s):
        s.instance = services.update_invoice(
            invoice=self.get_object(),
            actor=self.request.user,
            data=s.validated_data,
            expected_version=int(self.request.headers.get("If-Match", 0)),
        )

    def perform_destroy(self, instance):
        services.delete_invoice(invoice=instance)


class VerifyView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = InvoiceSerializer

    def post(self, r, pk):
        invoice = generics.get_object_or_404(
            Invoice,
            pk=pk,
            buyer__memberships__user=r.user,
            buyer__memberships__scopes__contains=["verify_invoice"],
        )
        services.verify_invoice(
            invoice=invoice, actor=r.user, correlation_id=getattr(r, "correlation_id", "")
        )
        return Response(InvoiceSerializer(invoice).data)


class DisputeView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = DisputeSerializer

    def post(self, r, pk):
        invoice = generics.get_object_or_404(Invoice, pk=pk, buyer__memberships__user=r.user)
        s = DisputeSerializer(data=r.data)
        s.is_valid(raise_exception=True)
        att = Document.objects.filter(pk=s.validated_data.get("attachment_id")).first()
        services.dispute_invoice(
            invoice=invoice, actor=r.user, reason=s.validated_data["reason"], attachment=att
        )
        return Response(InvoiceSerializer(invoice).data)


class BulkCommitView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = BulkSerializer

    def post(self, r):
        s = BulkSerializer(data=r.data)
        s.is_valid(raise_exception=True)
        rows = []
        for row in s.validated_data["rows"]:
            item = InvoiceSerializer(data=row)
            item.is_valid(raise_exception=True)
            if not UserMembership.objects.filter(
                user=r.user, organization=item.validated_data["issuer"], is_active=True
            ).exists():
                raise DomainError(
                    "forbidden_issuer",
                    "اجازه صدور فاکتور برای یکی از سازمان‌ها را ندارید.",
                    status_code=403,
                )
            rows.append(item.validated_data)
        return Response(
            services.bulk_commit(
                actor=r.user,
                rows=rows,
                key=r.headers.get("Idempotency-Key", ""),
            )
        )


class BulkPreviewView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = BulkSerializer

    def post(self, request):
        serializer = BulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid, invalid, seen = [], [], set()
        for index, row in enumerate(serializer.validated_data["rows"], start=1):
            item = InvoiceSerializer(data=row)
            number_key = (str(row.get("issuer")), str(row.get("number")))
            if number_key in seen:
                invalid.append({"row": index, "errors": ["شماره فاکتور در فایل تکراری است."]})
            elif item.is_valid():
                seen.add(number_key)
                valid.append({"row": index, "data": item.data})
            else:
                invalid.append({"row": index, "errors": item.errors})
        return Response({"valid": valid, "invalid": invalid})
