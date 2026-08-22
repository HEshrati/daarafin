from rest_framework import serializers

from apps.medicines.models import Medicine, MedicineInsurancePrice


class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = (
            "id",
            "external_id",
            "name",
            "strength",
            "molecule",
            "route",
            "dosage_form",
            "atc_code",
            "formulary_code",
            "access_level",
            "drug_type",
            "clinical_use",
            "formulary_entry_date",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class MedicineInsurancePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineInsurancePrice
        fields = (
            "id",
            "medicine",
            "generic_code",
            "generic_name",
            "insurance_price",
            "subsidy_price",
            "insurance_type",
            "letter_shamsi_date",
            "letter_miladi_date",
            "package_number",
            "last_update_date",
            "created_at",
        )


class MedicineImportSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField(min_value=1, required=False)
    file = serializers.FileField()


class MedicineImportErrorSerializer(serializers.Serializer):
    row = serializers.IntegerField()
    message = serializers.CharField()


class MedicineImportResultSerializer(serializers.Serializer):
    created = serializers.IntegerField(min_value=0)
    updated = serializers.IntegerField(min_value=0)
    errors = MedicineImportErrorSerializer(many=True)
