from django.db import migrations


ROLE_SCOPES = {
    "owner": {
        "manage_organization",
        "manage_members",
        "manage_onboarding",
        "view_bank_accounts",
        "change_bank_account",
        "create_invoice",
        "dispute_invoice",
        "view_invoice",
        "manage_facility",
        "reserve_facility",
        "view_facility",
    },
    "operator": {
        "create_invoice",
        "dispute_invoice",
        "view_invoice",
        "reserve_facility",
        "view_facility",
    },
    "approver": {"approve_financing", "reject_financing", "verify_invoice", "view_invoice"},
    "risk_expert": {
        "view_risk",
        "assess_risk",
        "review_onboarding",
        "verify_invoice",
        "view_invoice",
    },
    "bank_finance": {"view_ledger", "approve_payment"},
    "support": {"view_support_case"},
}


def add_default_role_scopes(apps, schema_editor):
    membership_model = apps.get_model("organizations", "UserMembership")
    for membership in membership_model.objects.all().iterator():
        merged = set(membership.scopes or ()) | ROLE_SCOPES.get(membership.role, set())
        if merged != set(membership.scopes or ()):
            membership.scopes = sorted(merged)
            membership.save(update_fields=("scopes",))


class Migration(migrations.Migration):
    dependencies = [("organizations", "0001_initial")]

    operations = [migrations.RunPython(add_default_role_scopes, migrations.RunPython.noop)]
