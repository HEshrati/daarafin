from rest_framework import serializers

from apps.organizations.models import BankAccount, Organization, UserMembership


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name", "type", "national_id", "status", "risk_tier")
        read_only_fields = ("status",)


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMembership
        fields = ("id", "user", "role", "scopes", "is_active")


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ("id", "iban", "is_active")
