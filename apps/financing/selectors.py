from django.db import models
from django.utils import timezone

from .models import FinancingRequest, Policy


def active_policy():
    return (
        Policy.objects.filter(is_active=True, effective_from__lte=timezone.now())
        .order_by("-effective_from", "-version")
        .first()
    )


def financing_requests_for_user(user):
    queryset = FinancingRequest.objects.select_related(
        "quote__policy",
        "invoice__issuer",
        "invoice__buyer",
        "facility__lender",
        "facility__borrower",
        "bank_account",
        "created_by",
        "approved_by",
    ).prefetch_related(
        "invoice__issuer__bank_accounts", "quote__invoice_lines", "quote__lines", "history"
    )
    if user.is_staff:
        return queryset

    organization_ids = [
        organization_id
        for organization_id, scopes in user.memberships.filter(is_active=True).values_list(
            "organization_id", "scopes"
        )
        if "view_financing" in scopes
    ]
    return queryset.filter(
        models.Q(invoice__issuer_id__in=organization_ids)
        | models.Q(facility__lender_id__in=organization_ids)
    ).distinct()
