from rest_framework import serializers

from apps.organizations.models import (
    BankAccount,
    DistributorBranch,
    Organization,
    OrganizationContact,
    PharmacyProfile,
    UserMembership,
)


class PharmacyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyProfile
        fields = (
            "university_name",
            "service_type",
            "pharmacy_type",
            "customer_national_id",
            "owner_name",
            "responsible_national_id",
            "founder_mobile",
            "landline",
        )


class OrganizationSerializer(serializers.ModelSerializer):
    pharmacy_profile = PharmacyProfileSerializer(read_only=True)

    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "type",
            "national_id",
            "gln",
            "status",
            "risk_tier",
            "company_type",
            "country",
            "province",
            "county",
            "city",
            "address",
            "postal_code",
            "phone",
            "email",
            "pharmacy_profile",
        )
        read_only_fields = ("status",)


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMembership
        fields = ("id", "user", "role", "scopes", "is_active")


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ("id", "iban", "is_active")


class OrganizationContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationContact
        fields = ("id", "role", "full_name", "national_id", "mobile", "email")
        read_only_fields = ("id",)


class DistributorBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = DistributorBranch
        fields = (
            "id",
            "gln",
            "name",
            "postal_code",
            "province",
            "county",
            "city",
            "address",
        )
        read_only_fields = ("id",)
