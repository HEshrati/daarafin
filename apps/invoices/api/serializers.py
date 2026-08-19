from decimal import Decimal

from rest_framework import serializers

from apps.invoices.models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(
        max_digits=24, decimal_places=4, coerce_to_string=True, min_value=Decimal("0.0001")
    )

    class Meta:
        model = Invoice
        fields = (
            "id",
            "issuer",
            "buyer",
            "number",
            "amount",
            "due_date",
            "status",
            "version",
            "created_at",
        )
        read_only_fields = ("status", "version", "created_at")


class DisputeSerializer(serializers.Serializer):
    reason = serializers.CharField()
    attachment_id = serializers.IntegerField(required=False)


class BulkSerializer(serializers.Serializer):
    rows = serializers.ListField(child=serializers.DictField())
