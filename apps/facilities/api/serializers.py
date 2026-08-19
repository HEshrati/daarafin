from decimal import Decimal

from rest_framework import serializers

from apps.facilities.models import Facility, FacilityReservation


class FacilitySerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()
    limit = serializers.DecimalField(max_digits=24, decimal_places=4, coerce_to_string=True)
    utilized_amount = serializers.DecimalField(
        max_digits=24, decimal_places=4, coerce_to_string=True, read_only=True
    )

    class Meta:
        model = Facility
        fields = ("id", "lender", "borrower", "limit", "utilized_amount", "available", "expiry")

    def get_available(self, obj) -> str:
        return str(obj.available_amount)


class ReserveSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=24, decimal_places=4, min_value=Decimal("0.0001"))


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityReservation
        fields = ("id", "amount", "created_at")
