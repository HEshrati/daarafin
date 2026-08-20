import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0002_invoice_invoice_amount_positive_and_more"),
        ("medicines", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="InvoiceLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(blank=True, default="", max_length=512)),
                ("quantity", models.DecimalField(decimal_places=4, max_digits=18)),
                ("unit_price", models.DecimalField(decimal_places=4, max_digits=24)),
                ("line_amount", models.DecimalField(decimal_places=4, max_digits=24)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "invoice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lines",
                        to="invoices.invoice",
                    ),
                ),
                (
                    "medicine",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="invoice_lines",
                        to="medicines.medicine",
                    ),
                ),
            ],
            options={"ordering": ("sort_order", "pk")},
        ),
        migrations.AddConstraint(
            model_name="invoiceline",
            constraint=models.CheckConstraint(
                condition=models.Q(("quantity__gt", 0)),
                name="invoice_line_quantity_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="invoiceline",
            constraint=models.CheckConstraint(
                condition=models.Q(("unit_price__gte", 0)),
                name="invoice_line_unit_price_nonneg",
            ),
        ),
        migrations.AddConstraint(
            model_name="invoiceline",
            constraint=models.CheckConstraint(
                condition=models.Q(("line_amount__gte", 0)),
                name="invoice_line_amount_nonneg",
            ),
        ),
    ]
