from django.db import migrations

NEW_SCOPES_BY_ROLE = {
    "owner": ["import_master_data", "view_medicines", "manage_medicines"],
    "operator": ["import_master_data", "view_medicines"],
    "approver": ["view_medicines"],
    "risk_expert": ["view_medicines"],
    "bank_finance": ["view_medicines"],
    "support": ["view_medicines"],
}


def forwards(apps, schema_editor):
    UserMembership = apps.get_model("organizations", "UserMembership")
    for membership in UserMembership.objects.all().iterator():
        extras = NEW_SCOPES_BY_ROLE.get(membership.role, [])
        scopes = list(membership.scopes or [])
        changed = False
        for scope in extras:
            if scope not in scopes:
                scopes.append(scope)
                changed = True
        if changed:
            membership.scopes = scopes
            membership.save(update_fields=["scopes"])


def backwards(apps, schema_editor):
    UserMembership = apps.get_model("organizations", "UserMembership")
    remove = {
        "import_master_data",
        "view_medicines",
        "manage_medicines",
    }
    for membership in UserMembership.objects.all().iterator():
        scopes = [s for s in (membership.scopes or []) if s not in remove]
        if scopes != list(membership.scopes or []):
            membership.scopes = scopes
            membership.save(update_fields=["scopes"])


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0004_master_data_profiles"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
