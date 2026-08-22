from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.facilities.models import Facility, FacilityReservation
from apps.organizations.models import Organization


class FacilitySerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()
    limit = serializers.DecimalField(
        max_digits=24,
        decimal_places=4,
        coerce_to_string=True,
        min_value=Decimal("0.0001"),
    )
    utilized_amount = serializers.DecimalField(
        max_digits=24, decimal_places=4, coerce_to_string=True, read_only=True
    )

    class Meta:
        model = Facility
        fields = ("id", "lender", "borrower", "limit", "utilized_amount", "available", "expiry")

    def validate(self, attrs):
        lender = attrs.get("lender", getattr(self.instance, "lender", None))
        borrower = attrs.get("borrower", getattr(self.instance, "borrower", None))
        if lender == borrower:
            raise serializers.ValidationError("اعتباردهنده و اعتبارگیرنده باید متفاوت باشند.")
        if lender is not None and lender.type != Organization.Type.BANK:
            raise serializers.ValidationError({"lender": "اعتباردهنده باید یک سازمان بانکی باشد."})
        if borrower is not None and borrower.type == Organization.Type.BANK:
            raise serializers.ValidationError(
                {"borrower": "اعتبارگیرنده نمی‌تواند سازمان بانکی باشد."}
            )
        if attrs.get("expiry") and attrs["expiry"] < timezone.localdate():
            raise serializers.ValidationError("تاریخ انقضای تسهیلات نمی‌تواند در گذشته باشد.")
        return attrs

    def get_available(self, obj) -> str:
        return str(obj.available_amount)


class ReserveSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=24, decimal_places=4, min_value=Decimal("0.0001"))


class ReservationSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(
        max_digits=24, decimal_places=4, coerce_to_string=True, read_only=True
    )

    class Meta:
        model = FacilityReservation
        fields = ("id", "amount", "created_at")
