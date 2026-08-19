from rest_framework import generics
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Document
from apps.invoices import selectors, services
from common.errors import DomainError
from common.permissions import ensure_active_scope

from .serializers import (
    BulkSerializer,
    DisputeSerializer,
    InvoiceFilterSerializer,
    InvoiceSerializer,
)


class InvoicePagination(CursorPagination):
    ordering = ("-created_at", "-pk")


def parse_if_match(value: str | None) -> int:
    if not value:
        raise DomainError("if_match_required", "هدر If-Match الزامی است.", status_code=428)
    normalized = value.removeprefix("W/").strip('"')
    try:
        version = int(normalized)
    except ValueError as exc:
        raise DomainError("invalid_if_match", "هدر If-Match معتبر نیست.") from exc
    if version < 1:
        raise DomainError("invalid_if_match", "هدر If-Match معتبر نیست.")
    return version


class InvoiceListCreateView(generics.ListCreateAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = InvoicePagination

    def get_queryset(self):
        qs = selectors.invoices_for_user(self.request.user)
        filters = InvoiceFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        values = filters.validated_data
        if "status" in values:
            qs = qs.filter(status=values["status"])
        if "buyer" in values:
            qs = qs.filter(buyer_id=values["buyer"])
        if "due_date" in values:
            qs = qs.filter(due_date=values["due_date"])
        return qs.distinct()

    def perform_create(self, s):
        ensure_active_scope(
            user=self.request.user,
            organization_id=s.validated_data["issuer"].pk,
            scope="create_invoice",
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
        return selectors.invoices_for_user(self.request.user)

    def perform_update(self, s):
        invoice = self.get_object()
        ensure_active_scope(
            user=self.request.user,
            organization_id=invoice.issuer_id,
            scope="create_invoice",
        )
        target_issuer = s.validated_data.get("issuer", invoice.issuer)
        ensure_active_scope(
            user=self.request.user,
            organization_id=target_issuer.pk,
            scope="create_invoice",
        )
        s.instance = services.update_invoice(
            invoice=invoice,
            actor=self.request.user,
            data=s.validated_data,
            expected_version=parse_if_match(self.request.headers.get("If-Match")),
            correlation_id=getattr(self.request, "correlation_id", ""),
        )

    def perform_destroy(self, instance):
        ensure_active_scope(
            user=self.request.user,
            organization_id=instance.issuer_id,
            scope="create_invoice",
        )
        services.delete_invoice(
            invoice=instance,
            actor=self.request.user,
            correlation_id=getattr(self.request, "correlation_id", ""),
        )


class VerifyView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = InvoiceSerializer

    def post(self, r, pk):
        invoice = generics.get_object_or_404(
            selectors.invoices_for_user(r.user),
            pk=pk,
        )
        ensure_active_scope(user=r.user, organization_id=invoice.buyer_id, scope="verify_invoice")
        invoice = services.verify_invoice(
            invoice=invoice, actor=r.user, correlation_id=getattr(r, "correlation_id", "")
        )
        return Response(InvoiceSerializer(invoice).data)


class DisputeView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = DisputeSerializer

    def post(self, r, pk):
        invoice = generics.get_object_or_404(
            selectors.invoices_for_user(r.user),
            pk=pk,
        )
        s = DisputeSerializer(data=r.data)
        s.is_valid(raise_exception=True)
        ensure_active_scope(user=r.user, organization_id=invoice.buyer_id, scope="dispute_invoice")
        attachment_id = s.validated_data.get("attachment_id")
        attachment = None
        if attachment_id is not None:
            attachment = generics.get_object_or_404(
                Document,
                pk=attachment_id,
                scan_status=Document.ScanStatus.CLEAN,
                onboarding_case__organization=invoice.buyer,
            )
        invoice = services.dispute_invoice(
            invoice=invoice,
            actor=r.user,
            reason=s.validated_data["reason"],
            attachment=attachment,
            correlation_id=getattr(r, "correlation_id", ""),
        )
        return Response(InvoiceSerializer(invoice).data)


class BulkCommitView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = BulkSerializer

    def post(self, r):
        s = BulkSerializer(data=r.data)
        s.is_valid(raise_exception=True)
        rows = []
        seen = set()
        for row in s.validated_data["rows"]:
            item = InvoiceSerializer(data=row)
            item.is_valid(raise_exception=True)
            number_key = (item.validated_data["issuer"].pk, item.validated_data["number"])
            if number_key in seen:
                raise DomainError("duplicate_bulk_row", "شماره فاکتور در درخواست تکراری است.")
            ensure_active_scope(
                user=r.user,
                organization_id=item.validated_data["issuer"].pk,
                scope="create_invoice",
            )
            seen.add(number_key)
            rows.append(item.validated_data)
        return Response(
            services.bulk_commit(
                actor=r.user,
                rows=rows,
                key=r.headers.get("Idempotency-Key", ""),
                correlation_id=getattr(r, "correlation_id", ""),
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
            if item.is_valid():
                issuer = item.validated_data["issuer"]
                number_key = (issuer.pk, item.validated_data["number"])
                if number_key in seen:
                    invalid.append({"row": index, "errors": ["شماره فاکتور در فایل تکراری است."]})
                elif not selectors.user_can_issue_for(request.user, issuer.pk):
                    invalid.append({"row": index, "errors": ["دسترسی صادرکننده وجود ندارد."]})
                else:
                    seen.add(number_key)
                    valid.append({"row": index, "data": item.data})
            else:
                invalid.append({"row": index, "errors": item.errors})
        return Response({"valid": valid, "invalid": invalid})


class SubmitView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = InvoiceSerializer

    def post(self, request, pk):
        invoice = generics.get_object_or_404(
            selectors.invoices_for_user(request.user),
            pk=pk,
        )
        ensure_active_scope(
            user=request.user,
            organization_id=invoice.issuer_id,
            scope="create_invoice",
        )
        invoice = services.submit_invoice(
            invoice=invoice,
            actor=request.user,
            correlation_id=getattr(request, "correlation_id", ""),
        )
        return Response(InvoiceSerializer(invoice).data)
