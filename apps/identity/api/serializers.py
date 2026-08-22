from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.identity.models import User
from apps.organizations.models import UserMembership


class MembershipOrganizationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    type = serializers.CharField()


class UserMembershipSummarySerializer(serializers.ModelSerializer):
    organization = MembershipOrganizationSerializer(read_only=True)

    class Meta:
        model = UserMembership
        fields = ("id", "role", "scopes", "organization")


class MeSerializer(serializers.ModelSerializer):
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "mobile", "is_mfa_enabled", "memberships")

    @extend_schema_field(UserMembershipSummarySerializer(many=True))
    def get_memberships(self, user) -> list[dict]:
        memberships = (
            UserMembership.objects.filter(user=user, is_active=True)
            .select_related("organization")
            .order_by("id")
        )
        return UserMembershipSummarySerializer(memberships, many=True).data


class SessionSerializer(serializers.Serializer):
    current = serializers.BooleanField()
    authenticated_at = serializers.DateTimeField()
