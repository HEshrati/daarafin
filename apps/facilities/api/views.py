from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.facilities import selectors, services
from apps.facilities.models import FacilityReservation
from common.permissions import ensure_active_scope

from .serializers import FacilitySerializer, ReservationSerializer, ReserveSerializer


class FacilityListCreateView(generics.ListCreateAPIView):
    serializer_class = FacilitySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return selectors.facilities_for_user(self.request.user)

    def perform_create(self, serializer):
        ensure_active_scope(
            user=self.request.user,
            organization_id=serializer.validated_data["lender"].pk,
            scope="manage_facility",
        )
        serializer.instance = services.create_facility(
            actor=self.request.user,
            data=serializer.validated_data,
            correlation_id=getattr(self.request, "correlation_id", ""),
        )


class FacilityDetailView(generics.RetrieveAPIView):
    serializer_class = FacilitySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return selectors.facilities_for_user(self.request.user)


class ReserveView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ReserveSerializer

    def post(self, r, pk):
        facility = generics.get_object_or_404(
            selectors.facilities_for_user(r.user),
            pk=pk,
        )
        s = ReserveSerializer(data=r.data)
        s.is_valid(raise_exception=True)
        ensure_active_scope(
            user=r.user,
            organization_id=facility.borrower_id,
            scope="reserve_facility",
        )
        return Response(
            services.reserve_facility(
                facility_id=facility.pk,
                amount=s.validated_data["amount"],
                key=r.headers.get("Idempotency-Key", ""),
                actor=r.user,
                correlation_id=getattr(r, "correlation_id", ""),
            )
        )


class HistoryView(generics.ListAPIView):
    serializer_class = ReservationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return FacilityReservation.objects.filter(
            facility_id=self.kwargs["pk"],
            facility__in=selectors.facilities_for_user(self.request.user),
        )
