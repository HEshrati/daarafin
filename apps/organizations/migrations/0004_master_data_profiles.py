# Generated manually for master-data expansions

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0003_add_financing_role_scopes"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="organization",
            name="city",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="organization",
            name="company_type",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="organization",
            name="country",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="organization",
            name="county",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="organization",
            name="email",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
        migrations.AddField(
            model_name="organization",
            name="gln",
            field=models.CharField(blank=True, db_index=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="organization",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="organization",
            name="postal_code",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="organization",
            name="province",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.CreateModel(
            name="DistributorBranch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("gln", models.CharField(db_index=True, max_length=32)),
                ("name", models.CharField(blank=True, default="", max_length=255)),
                ("postal_code", models.CharField(blank=True, default="", max_length=20)),
                ("province", models.CharField(blank=True, default="", max_length=64)),
                ("county", models.CharField(blank=True, default="", max_length=64)),
                ("city", models.CharField(blank=True, default="", max_length=64)),
                ("address", models.TextField(blank=True, default="")),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="branches",
                        to="organizations.organization",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="OrganizationContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("ceo", "مدیرعامل"),
                            ("technical", "مسئول فنی"),
                            ("owner", "مالک / رابط"),
                            ("other", "سایر"),
                        ],
                        max_length=16,
                    ),
                ),
                ("full_name", models.CharField(blank=True, default="", max_length=255)),
                ("national_id", models.CharField(blank=True, default="", max_length=20)),
                ("mobile", models.CharField(blank=True, default="", max_length=32)),
                ("email", models.EmailField(blank=True, default="", max_length=254)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contacts",
                        to="organizations.organization",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PharmacyProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("university_name", models.CharField(blank=True, default="", max_length=255)),
                ("service_type", models.CharField(blank=True, default="", max_length=64)),
                ("pharmacy_type", models.CharField(blank=True, default="", max_length=128)),
                ("customer_national_id", models.CharField(blank=True, default="", max_length=20)),
                ("owner_name", models.CharField(blank=True, default="", max_length=255)),
                ("responsible_national_id", models.CharField(blank=True, default="", max_length=20)),
                ("founder_mobile", models.CharField(blank=True, default="", max_length=32)),
                ("landline", models.CharField(blank=True, default="", max_length=32)),
                (
                    "organization",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pharmacy_profile",
                        to="organizations.organization",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="organizationcontact",
            index=models.Index(fields=["organization", "role"], name="organizatio_organiz_6b0c1b_idx"),
        ),
        migrations.AddIndex(
            model_name="organizationcontact",
            index=models.Index(fields=["national_id"], name="organizatio_nationa_0d2f1a_idx"),
        ),
        migrations.AddConstraint(
            model_name="distributorbranch",
            constraint=models.UniqueConstraint(
                fields=("organization", "gln"), name="unique_org_branch_gln"
            ),
        ),
    ]
