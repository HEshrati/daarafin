from django.db import transaction

from .models import Organization, UserMembership

DEFAULT_ROLE_SCOPES = {
    "owner": ["manage_organization", "manage_members", "view_bank_accounts", "change_bank_account"],
    "operator": ["create_invoice", "view_invoice"],
    "approver": ["approve_financing", "reject_financing", "view_invoice"],
    "risk_expert": ["view_risk", "assess_risk"],
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
        scopes=["manage_organization", "manage_members", "view_bank_accounts"],
    )
    return organization


@transaction.atomic
def add_member(*, organization, data):
    data.setdefault("scopes", DEFAULT_ROLE_SCOPES[data["role"]].copy())
    return UserMembership.objects.create(organization=organization, **data)
