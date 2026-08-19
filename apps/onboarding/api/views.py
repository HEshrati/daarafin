from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.onboarding import selectors, services
from apps.onboarding.models import OnboardingCase
from apps.organizations.models import Organization, UserMembership
from common.errors import DomainError

from .serializers import CaseCreateSerializer, CaseSerializer, DecisionSerializer


class CaseListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CaseSerializer

    def get_queryset(self):
        return selectors.cases_for_user(self.request.user)

    def create(self, request):
        data = CaseCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        org, _ = Organization.objects.get_or_create(
            national_id=v["national_id"],
            defaults={"name": v["name"], "type": v["organization_type"]},
        )
        UserMembership.objects.get_or_create(
            user=request.user,
            organization=org,
            role="owner",
            defaults={"scopes": ["manage_onboarding"]},
        )
        case = OnboardingCase.objects.create(organization=org, requested_by=request.user)
        return Response(CaseSerializer(case).data, status=status.HTTP_201_CREATED)


class SubmitView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CaseSerializer

    def post(self, request, pk):
        case = generics.get_object_or_404(selectors.cases_for_user(request.user), pk=pk)
        services.submit_case(
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
        membership = UserMembership.objects.filter(
            user=request.user, organization=case.organization, is_active=True
        ).first()
        if membership is None or "review_onboarding" not in membership.scopes:
            raise DomainError(
                "onboarding_review_forbidden",
                "دسترسی تصمیم‌گیری پرونده را ندارید.",
                status_code=403,
            )
        s = DecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.transition_case(
            case=case,
            target=s.validated_data["decision"],
            actor=request.user,
            reason=s.validated_data.get("reason", ""),
            correlation_id=getattr(request, "correlation_id", ""),
        )
        return Response(CaseSerializer(case).data)
