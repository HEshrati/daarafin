from django.db import models

from .models import Invoice

INVOICE_SCOPES = {"view_invoice", "create_invoice", "verify_invoice", "dispute_invoice"}


def invoices_for_user(user):
    if user.is_staff:
        return Invoice.objects.all()
    organization_ids = [
        organization_id
        for organization_id, scopes in user.memberships.filter(is_active=True).values_list(
            "organization_id", "scopes"
        )
        if INVOICE_SCOPES.intersection(scopes)
    ]
    return Invoice.objects.filter(
        models.Q(issuer_id__in=organization_ids) | models.Q(buyer_id__in=organization_ids)
    )


def user_can_issue_for(user, organization_id) -> bool:
    if user.is_staff:
        return True
    return any(
        "create_invoice" in scopes
        for scopes in user.memberships.filter(
            organization_id=organization_id, is_active=True
        ).values_list("scopes", flat=True)
    )
