from rest_framework import serializers

from apps.onboarding.models import OnboardingCase
from apps.organizations.models import Organization


class CaseCreateSerializer(serializers.Serializer):
    organization_type = serializers.ChoiceField(choices=Organization.Type.choices)
    national_id = serializers.CharField()
    name = serializers.CharField()


class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingCase
        fields = (
            "id",
            "organization",
            "status",
            "reason",
            "requested_by",
            "reviewed_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approved", "rejected", "need_changes"))
    reason = serializers.CharField(required=False, allow_blank=True)
