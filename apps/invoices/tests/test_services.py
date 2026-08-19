from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.identity.tests.factories import UserFactory
from apps.invoices.models import Invoice
from apps.invoices.services import update_invoice
from apps.organizations.models import Organization
from common.errors import DomainError

pytestmark = pytest.mark.django_db


def invoice_data():
    user = UserFactory()
    issuer = Organization.objects.create(name="الف", type="manufacturer", national_id="11111111111")
    buyer = Organization.objects.create(name="ب", type="pharmacy", national_id="22222222222")
    return user, issuer, buyer


def test_unique_invoice_number_per_issuer():
    user, issuer, buyer = invoice_data()
    Invoice.objects.create(
        issuer=issuer,
        buyer=buyer,
        number="1",
        amount=Decimal("10"),
        due_date=date.today(),
        created_by=user,
    )
    with pytest.raises(IntegrityError):
        Invoice.objects.create(
            issuer=issuer,
            buyer=buyer,
            number="1",
            amount=Decimal("10"),
            due_date=date.today(),
            created_by=user,
        )


def test_optimistic_conflict():
    user, issuer, buyer = invoice_data()
    invoice = Invoice.objects.create(
        issuer=issuer,
        buyer=buyer,
        number="1",
        amount=Decimal("10"),
        due_date=date.today(),
        created_by=user,
    )
    with pytest.raises(DomainError):
        update_invoice(
            invoice=invoice, actor=user, data={"amount": Decimal("11")}, expected_version=2
        )
