from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.financing import selectors, services
from apps.financing.models import FinancingQuote, FinancingRequest
from apps.invoices import selectors as invoice_selectors
from common.errors import DomainError
from common.permissions import ensure_active_scope

from .serializers import (
    DisburseSerializer,
    FinancingRequestSerializer,
    QuoteCreateSerializer,
    QuoteSerializer,
    RejectSerializer,
    RequestCreateSerializer,
)


class QuoteCreateView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = QuoteCreateSerializer

    @extend_schema(request=QuoteCreateSerializer, responses={201: QuoteSerializer})
    def post(self, request):
        serializer = QuoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice_ids = serializer.validated_data["invoice_ids"]
        visible_invoices = list(
            invoice_selectors.invoices_for_user(request.user).filter(pk__in=invoice_ids)
        )
        if len(visible_invoices) != len(invoice_ids):
            raise DomainError("invoice_not_found", "یک یا چند فاکتور پیدا نشد.", status_code=404)
        for invoice in visible_invoices:
            ensure_active_scope(
                user=request.user,
                organization_id=invoice.issuer_id,
                scope="create_financing",
            )
        quote = services.create_quote(
            actor=request.user,
            invoice_ids=invoice_ids,
            amount=serializer.validated_data["amount"],
            term_days=serializer.validated_data["term"],
            correlation_id=getattr(request, "correlation_id", ""),
        )
        quote = (
            FinancingQuote.objects.select_related("policy", "request")
            .prefetch_related("invoice_lines", "lines")
            .get(pk=quote.pk)
        )
        return Response(QuoteSerializer(quote).data, status=status.HTTP_201_CREATED)


class RequestListCreateView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RequestCreateSerializer

    @extend_schema(responses=FinancingRequestSerializer(many=True))
    def get(self, request):
        requests = selectors.financing_requests_for_user(request.user).order_by(
            "-created_at", "-pk"
        )
        return Response(
            FinancingRequestSerializer(requests, many=True, context={"request": request}).data
        )

    @extend_schema(request=RequestCreateSerializer, responses=FinancingRequestSerializer)
    def post(self, request):
        serializer = RequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        financing_request = generics.get_object_or_404(
            FinancingRequest.objects.select_related("invoice", "quote"),
            quote_id=serializer.validated_data["quote_id"],
            created_by=request.user,
        )
        ensure_active_scope(
            user=request.user,
            organization_id=financing_request.invoice.issuer_id,
            scope="create_financing",
        )
        financing_request = services.submit_request(
            request=financing_request,
            facility_id=serializer.validated_data["facility_id"],
            key=request.headers.get("Idempotency-Key", ""),
            actor=request.user,
            correlation_id=getattr(request, "correlation_id", ""),
        )
        return _request_response(request, financing_request)


class RequestDetailView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FinancingRequestSerializer

    def get_queryset(self):
        return selectors.financing_requests_for_user(self.request.user)


class ApproveView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FinancingRequestSerializer

    @extend_schema(request=None, responses=FinancingRequestSerializer)
    def post(self, request, pk):
        financing_request = generics.get_object_or_404(
            selectors.financing_requests_for_user(request.user), pk=pk
        )
        ensure_active_scope(
            user=request.user,
            organization_id=_lender_id(financing_request),
            scope="approve_financing",
        )
        financing_request = services.approve_request(
            request=financing_request,
            key=request.headers.get("Idempotency-Key", ""),
            actor=request.user,
            correlation_id=getattr(request, "correlation_id", ""),
        )
        return _request_response(request, financing_request)


class RejectView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RejectSerializer

    @extend_schema(request=RejectSerializer, responses=FinancingRequestSerializer)
    def post(self, request, pk):
        financing_request = generics.get_object_or_404(
            selectors.financing_requests_for_user(request.user), pk=pk
        )
        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ensure_active_scope(
            user=request.user,
            organization_id=_lender_id(financing_request),
            scope="reject_financing",
        )
        financing_request = services.reject_request(
            request=financing_request,
            reason=serializer.validated_data["reason"],
            key=request.headers.get("Idempotency-Key", ""),
            actor=request.user,
            correlation_id=getattr(request, "correlation_id", ""),
        )
        return _request_response(request, financing_request)


class DisburseView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = DisburseSerializer

    @extend_schema(request=DisburseSerializer, responses=FinancingRequestSerializer)
    def post(self, request, pk):
        financing_request = generics.get_object_or_404(
            selectors.financing_requests_for_user(request.user), pk=pk
        )
        serializer = DisburseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ensure_active_scope(
            user=request.user,
            organization_id=_lender_id(financing_request),
            scope="disburse_financing",
        )
        financing_request = services.disburse_request(
            request=financing_request,
            bank_account_id=serializer.validated_data["bank_account_id"],
            key=request.headers.get("Idempotency-Key", ""),
            actor=request.user,
            correlation_id=getattr(request, "correlation_id", ""),
        )
        return _request_response(request, financing_request)


def _lender_id(financing_request):
    if financing_request.facility_id is None:
        raise DomainError("facility_required", "برای این درخواست خط اعتباری ثبت نشده است.")
    return financing_request.facility.lender_id


def _request_response(request, financing_request):
    return Response(
        FinancingRequestSerializer(financing_request, context={"request": request}).data
    )
