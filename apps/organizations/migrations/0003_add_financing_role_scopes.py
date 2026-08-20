from django.db import migrations


FINANCING_SCOPES = {
    "owner": {"create_financing", "view_financing"},
    "operator": {"create_financing", "view_financing"},
    "approver": {"approve_financing", "reject_financing", "view_financing"},
    "bank_finance": {"disburse_financing", "view_financing"},
}


def add_financing_scopes(apps, schema_editor):
    membership_model = apps.get_model("organizations", "UserMembership")
    for membership in membership_model.objects.all().iterator():
        merged = set(membership.scopes or ()) | FINANCING_SCOPES.get(membership.role, set())
        if merged != set(membership.scopes or ()):
            membership.scopes = sorted(merged)
            membership.save(update_fields=("scopes",))


class Migration(migrations.Migration):
    dependencies = [("organizations", "0002_backfill_role_scopes")]

    operations = [migrations.RunPython(add_financing_scopes, migrations.RunPython.noop)]
