from django.db import models


class Medicine(models.Model):
    """دارو از فهرست رسمی (MedicineIndex)."""

    external_id = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=1024)
    strength = models.CharField(max_length=512, blank=True, default="")
    molecule = models.TextField(blank=True, default="")
    route = models.CharField(max_length=128, blank=True, default="")
    dosage_form = models.CharField(max_length=255, blank=True, default="")
    atc_code = models.CharField(max_length=64, blank=True, default="", db_index=True)
    formulary_code = models.CharField(max_length=64, blank=True, default="", db_index=True)
    access_level = models.CharField(max_length=128, blank=True, default="")
    drug_type = models.CharField(max_length=128, blank=True, default="")
    clinical_use = models.TextField(blank=True, default="")
    formulary_entry_date = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=("name",))]


class MedicineInsurancePrice(models.Model):
    """تاریخچه قیمت بیمه/یارانه (final_view_by_date)."""

    medicine = models.ForeignKey(
        Medicine,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="insurance_prices",
    )
    generic_code = models.CharField(max_length=32, db_index=True)
    generic_name = models.CharField(max_length=512, blank=True, default="")
    insurance_price = models.DecimalField(max_digits=24, decimal_places=4)
    subsidy_price = models.DecimalField(max_digits=24, decimal_places=4, default=0)
    insurance_type = models.CharField(max_length=32, blank=True, default="")
    letter_shamsi_date = models.CharField(max_length=32, blank=True, default="")
    letter_miladi_date = models.DateField(null=True, blank=True)
    package_number = models.CharField(max_length=64, blank=True, default="")
    last_update_date = models.DateField(null=True, blank=True)
    source_created_at = models.DateTimeField(null=True, blank=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=("generic_code", "letter_miladi_date")),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("generic_code", "letter_miladi_date", "package_number", "insurance_type"),
                name="unique_insurance_price_snapshot",
            )
        ]
