from django.db import models

from .models import Invoice


def invoices_for_user(user):
    return Invoice.objects.filter(
        models.Q(issuer__memberships__user=user) | models.Q(buyer__memberships__user=user)
    ).distinct()
