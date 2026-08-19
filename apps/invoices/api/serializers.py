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

    def validate(self, attrs):
        issuer = attrs.get("issuer", getattr(self.instance, "issuer", None))
        buyer = attrs.get("buyer", getattr(self.instance, "buyer", None))
        if issuer == buyer:
            raise serializers.ValidationError("صادرکننده و خریدار باید متفاوت باشند.")
        return attrs


class DisputeSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=5000, trim_whitespace=True)
    attachment_id = serializers.IntegerField(required=False)


class BulkSerializer(serializers.Serializer):
    rows = serializers.ListField(child=serializers.DictField(), min_length=1, max_length=1000)


class InvoiceFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Invoice.Status.choices, required=False)
    buyer = serializers.IntegerField(min_value=1, required=False)
    due_date = serializers.DateField(required=False)
