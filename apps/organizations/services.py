from django.db import transaction

from .models import Organization, UserMembership

DEFAULT_ROLE_SCOPES = {
    "owner": [
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
    ],
    "operator": [
        "create_invoice",
        "dispute_invoice",
        "view_invoice",
        "reserve_facility",
        "view_facility",
    ],
    "approver": ["approve_financing", "reject_financing", "verify_invoice", "view_invoice"],
    "risk_expert": [
        "view_risk",
        "assess_risk",
        "review_onboarding",
        "verify_invoice",
        "view_invoice",
    ],
    "bank_finance": ["view_ledger", "approve_payment"],
    "support": ["view_support_case"],
}


@transaction.atomic
def create_organization(*, actor, data):
    organization = Organization.objects.create(**data)
    UserMembership.objects.create(
        user=actor,
        organization=organization,
        role=UserMembership.Role.OWNER,
        scopes=DEFAULT_ROLE_SCOPES["owner"].copy(),
    )
    return organization


@transaction.atomic
def add_member(*, organization, data):
    data.setdefault("scopes", DEFAULT_ROLE_SCOPES[data["role"]].copy())
    return UserMembership.objects.create(organization=organization, **data)
