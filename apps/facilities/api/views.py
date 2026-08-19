from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.facilities import services
from apps.facilities.models import Facility, FacilityReservation

from .serializers import FacilitySerializer, ReservationSerializer, ReserveSerializer


class FacilityListCreateView(generics.ListCreateAPIView):
    serializer_class = FacilitySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return (
            Facility.objects.filter(borrower__memberships__user=self.request.user)
            | Facility.objects.filter(lender__memberships__user=self.request.user)
        ).distinct()


class FacilityDetailView(generics.RetrieveAPIView):
    serializer_class = FacilitySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return (
            Facility.objects.filter(borrower__memberships__user=self.request.user)
            | Facility.objects.filter(lender__memberships__user=self.request.user)
        ).distinct()


class ReserveView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ReserveSerializer

    def post(self, r, pk):
        facility = generics.get_object_or_404(
            Facility.objects.filter(borrower__memberships__user=r.user).distinct(), pk=pk
        )
        s = ReserveSerializer(data=r.data)
        s.is_valid(raise_exception=True)
        return Response(
            services.reserve_facility(
                facility_id=facility.pk,
                amount=s.validated_data["amount"],
                key=r.headers.get("Idempotency-Key", ""),
            )
        )


class HistoryView(generics.ListAPIView):
    serializer_class = ReservationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return FacilityReservation.objects.filter(
            facility_id=self.kwargs["pk"],
            facility__borrower__memberships__user=self.request.user,
        ).distinct()
