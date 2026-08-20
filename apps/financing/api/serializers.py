from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.financing.models import (
    FinancingQuote,
    FinancingQuoteLine,
    FinancingRequest,
    FinancingRequestHistory,
)


class QuoteCreateSerializer(serializers.Serializer):
    invoice_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False
    )
    amount = serializers.DecimalField(max_digits=24, decimal_places=4, min_value=Decimal("0.0001"))
    term = serializers.IntegerField(min_value=1, max_value=3650)

    def validate_invoice_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("شناسه فاکتور تکراری است.")
        return value


class QuoteLineSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(
        max_digits=24, decimal_places=4, coerce_to_string=True, read_only=True
    )

    class Meta:
        model = FinancingQuoteLine
        fields = ("kind", "amount")
        read_only_fields = fields


class QuoteSerializer(serializers.ModelSerializer):
    invoice_ids = serializers.SerializerMethodField()
    policy_version = serializers.IntegerField(source="policy.version", read_only=True)
    request_id = serializers.IntegerField(source="request.id", read_only=True)
    lines = QuoteLineSerializer(many=True, read_only=True)

    class Meta:
        model = FinancingQuote
        fields = (
            "id",
            "request_id",
            "invoice_ids",
            "policy_version",
            "principal",
            "term_days",
            "financing_fee",
            "platform_fee",
            "net_amount",
            "lines",
            "expires_at",
            "created_at",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.ListField(child=serializers.IntegerField()))
    def get_invoice_ids(self, obj) -> list[int]:
        return [line.invoice_id for line in obj.invoice_lines.all()]


class RequestHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancingRequestHistory
        fields = ("from_status", "to_status", "changed_by", "reason", "created_at")
        read_only_fields = fields


class EligibleBankAccountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    iban = serializers.CharField()


class FinancingRequestSerializer(serializers.ModelSerializer):
    quote = QuoteSerializer(read_only=True)
    history = RequestHistorySerializer(many=True, read_only=True)
    borrower = serializers.IntegerField(source="invoice.issuer_id", read_only=True)
    eligible_bank_accounts = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = FinancingRequest
        fields = (
            "id",
            "quote",
            "invoice",
            "borrower",
            "facility",
            "bank_account",
            "eligible_bank_accounts",
            "allowed_actions",
            "requested_amount",
            "term",
            "status",
            "rejection_reason",
            "created_by",
            "approved_by",
            "history",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    @extend_schema_field(EligibleBankAccountSerializer(many=True))
    def get_eligible_bank_accounts(self, obj) -> list[dict[str, int | str]]:
        return [
            {"id": account.pk, "iban": account.iban}
            for account in obj.invoice.issuer.bank_accounts.all()
            if account.is_active
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_allowed_actions(self, obj) -> list[str]:
        request = self.context.get("request")
        if request is None or obj.facility_id is None:
            return []
        user = request.user
        actions = []
        if obj.status == FinancingRequest.Status.REQUESTED and user.pk != obj.created_by_id:
            if self._has_scope(user, obj.facility.lender_id, "approve_financing"):
                actions.append("approve")
            if self._has_scope(user, obj.facility.lender_id, "reject_financing"):
                actions.append("reject")
        if obj.status == FinancingRequest.Status.APPROVED and self._has_scope(
            user, obj.facility.lender_id, "disburse_financing"
        ):
            actions.append("disburse")
        return actions

    def _has_scope(self, user, organization_id, scope):
        if user.is_staff:
            return True
        scope_map = getattr(self, "_active_scope_map", None)
        if scope_map is None:
            scope_map = {
                org_id: set(scopes)
                for org_id, scopes in user.memberships.filter(is_active=True).values_list(
                    "organization_id", "scopes"
                )
            }
            self._active_scope_map = scope_map
        return scope in scope_map.get(organization_id, set())


class RequestCreateSerializer(serializers.Serializer):
    quote_id = serializers.IntegerField(min_value=1)
    facility_id = serializers.IntegerField(min_value=1)


class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, max_length=2000)


class DisburseSerializer(serializers.Serializer):
    bank_account_id = serializers.IntegerField(min_value=1)


class DashboardPointSerializer(serializers.Serializer):
    x = serializers.CharField()
    y = serializers.FloatField()


class DashboardSeriesSerializer(serializers.Serializer):
    name = serializers.CharField()
    points = DashboardPointSerializer(many=True)


class DashboardChartSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=("line", "bar", "donut"))
    title = serializers.CharField()
    series = DashboardSeriesSerializer(many=True)


class DashboardKpiSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    value = serializers.CharField()
    unit = serializers.ChoiceField(choices=("IRR", "count", "percent"))


class DashboardTableColumnSerializer(serializers.Serializer):
    key = serializers.CharField()
    title = serializers.CharField()


class DashboardTableSerializer(serializers.Serializer):
    title = serializers.CharField()
    columns = DashboardTableColumnSerializer(many=True)
    rows = serializers.ListField(child=serializers.DictField())


class DashboardSerializer(serializers.Serializer):
    persona = serializers.CharField(allow_null=True)
    kpis = DashboardKpiSerializer(many=True)
    charts = DashboardChartSerializer(many=True)
    table = DashboardTableSerializer()
