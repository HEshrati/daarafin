import datetime
from decimal import Decimal

from django.db import migrations


def seed_default_policy(apps, schema_editor):
    policy = apps.get_model("financing", "Policy")
    policy.objects.get_or_create(
        version=1,
        defaults={
            "annual_rate": Decimal("0.240000"),
            "platform_fee_rate": Decimal("0.010000"),
            "platform_fee_flat": Decimal("0.0000"),
            "effective_from": datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            "is_active": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("financing", "0001_initial")]

    operations = [migrations.RunPython(seed_default_policy, migrations.RunPython.noop)]
