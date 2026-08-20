from decimal import Decimal

from rest_framework import serializers

from apps.invoices.models import Invoice, InvoiceLine
from apps.medicines.models import Medicine


class InvoiceLineSerializer(serializers.ModelSerializer):
    medicine_id = serializers.PrimaryKeyRelatedField(
        source="medicine",
        queryset=Medicine.objects.all(),
        allow_null=True,
        required=False,
    )
    quantity = serializers.DecimalField(
        max_digits=18, decimal_places=4, coerce_to_string=True, min_value=Decimal("0.0001")
    )
    unit_price = serializers.DecimalField(
        max_digits=24, decimal_places=4, coerce_to_string=True, min_value=Decimal("0")
    )
    line_amount = serializers.DecimalField(
        max_digits=24,
        decimal_places=4,
        coerce_to_string=True,
        required=False,
        min_value=Decimal("0"),
    )

    class Meta:
        model = InvoiceLine
        fields = (
            "id",
            "medicine_id",
            "description",
            "quantity",
            "unit_price",
            "line_amount",
            "sort_order",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        quantity = attrs.get("quantity")
        unit_price = attrs.get("unit_price")
        line_amount = attrs.get("line_amount")
        if quantity is not None and unit_price is not None:
            computed = (quantity * unit_price).quantize(Decimal("0.0001"))
            if line_amount is None:
                attrs["line_amount"] = computed
            elif abs(line_amount - computed) > Decimal("0.0001"):
                raise serializers.ValidationError(
                    "مبلغ خط با حاصل‌ضرب تعداد در قیمت واحد هم‌خوان نیست."
                )
        return attrs


class InvoiceSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(
        max_digits=24, decimal_places=4, coerce_to_string=True, min_value=Decimal("0.0001")
    )
    lines = InvoiceLineSerializer(many=True, required=False)

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
            "lines",
        )
        read_only_fields = ("status", "version", "created_at")

    def validate(self, attrs):
        issuer = attrs.get("issuer", getattr(self.instance, "issuer", None))
        buyer = attrs.get("buyer", getattr(self.instance, "buyer", None))
        if issuer == buyer:
            raise serializers.ValidationError("صادرکننده و خریدار باید متفاوت باشند.")
        lines = attrs.get("lines")
        if lines is not None:
            total = sum((line["line_amount"] for line in lines), Decimal("0"))
            amount = attrs.get("amount", getattr(self.instance, "amount", None))
            if amount is not None and abs(amount - total) > Decimal("0.0001"):
                raise serializers.ValidationError(
                    "مبلغ فاکتور باید برابر جمع مبلغ خطوط باشد."
                )
            if amount is None and lines:
                attrs["amount"] = total
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
