from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Medicine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=512)),
                ("strength", models.CharField(blank=True, default="", max_length=255)),
                ("molecule", models.CharField(blank=True, default="", max_length=512)),
                ("route", models.CharField(blank=True, default="", max_length=64)),
                ("dosage_form", models.CharField(blank=True, default="", max_length=128)),
                ("atc_code", models.CharField(blank=True, db_index=True, default="", max_length=32)),
                ("formulary_code", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("access_level", models.CharField(blank=True, default="", max_length=64)),
                ("drug_type", models.CharField(blank=True, default="", max_length=64)),
                ("clinical_use", models.CharField(blank=True, default="", max_length=255)),
                ("formulary_entry_date", models.CharField(blank=True, default="", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="MedicineInsurancePrice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("generic_code", models.CharField(db_index=True, max_length=32)),
                ("generic_name", models.CharField(blank=True, default="", max_length=512)),
                ("insurance_price", models.DecimalField(decimal_places=4, max_digits=24)),
                ("subsidy_price", models.DecimalField(decimal_places=4, default=0, max_digits=24)),
                ("insurance_type", models.CharField(blank=True, default="", max_length=32)),
                ("letter_shamsi_date", models.CharField(blank=True, default="", max_length=32)),
                ("letter_miladi_date", models.DateField(blank=True, null=True)),
                ("package_number", models.CharField(blank=True, default="", max_length=64)),
                ("last_update_date", models.DateField(blank=True, null=True)),
                ("source_created_at", models.DateTimeField(blank=True, null=True)),
                ("source_updated_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "medicine",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="insurance_prices",
                        to="medicines.medicine",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="medicine",
            index=models.Index(fields=["name"], name="medicines_m_name_3f8c2a_idx"),
        ),
        migrations.AddIndex(
            model_name="medicineinsuranceprice",
            index=models.Index(
                fields=["generic_code", "letter_miladi_date"],
                name="medicines_m_generic_7a1b2c_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="medicineinsuranceprice",
            constraint=models.UniqueConstraint(
                fields=("generic_code", "letter_miladi_date", "package_number", "insurance_type"),
                name="unique_insurance_price_snapshot",
            ),
        ),
    ]
