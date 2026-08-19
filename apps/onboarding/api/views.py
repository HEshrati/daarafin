from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.onboarding import selectors, services
from common.permissions import ensure_active_scope

from .serializers import CaseCreateSerializer, CaseSerializer, DecisionSerializer


class CaseListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CaseSerializer

    def get_queryset(self):
        return selectors.cases_for_user(self.request.user)

    def create(self, request):
        data = CaseCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        case = services.create_case(
            actor=request.user,
            correlation_id=getattr(request, "correlation_id", ""),
            **data.validated_data,
        )
        return Response(CaseSerializer(case).data, status=status.HTTP_201_CREATED)


class SubmitView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CaseSerializer

    def post(self, request, pk):
        case = generics.get_object_or_404(selectors.cases_for_user(request.user), pk=pk)
        ensure_active_scope(
            user=request.user,
            organization_id=case.organization_id,
            scope="manage_onboarding",
        )
        case = services.submit_case(
            case=case,
            actor=request.user,
            idempotency_key=request.headers.get("Idempotency-Key"),
            correlation_id=getattr(request, "correlation_id", ""),
        )
        return Response(CaseSerializer(case).data)


class DecisionView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = DecisionSerializer

    def post(self, request, pk):
        case = generics.get_object_or_404(selectors.cases_for_user(request.user), pk=pk)
        ensure_active_scope(
            user=request.user,
            organization_id=case.organization_id,
            scope="review_onboarding",
        )
        s = DecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        case = services.transition_case(
            case=case,
            target=s.validated_data["decision"],
            actor=request.user,
            reason=s.validated_data.get("reason", ""),
            correlation_id=getattr(request, "correlation_id", ""),
        )
        return Response(CaseSerializer(case).data)


class ReviewView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CaseSerializer

    def post(self, request, pk):
        case = generics.get_object_or_404(selectors.cases_for_user(request.user), pk=pk)
        ensure_active_scope(
            user=request.user,
            organization_id=case.organization_id,
            scope="review_onboarding",
        )
        case = services.transition_case(
            case=case,
            target="under_review",
            actor=request.user,
            correlation_id=getattr(request, "correlation_id", ""),
        )
        return Response(CaseSerializer(case).data)
