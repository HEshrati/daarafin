from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError
from rest_framework.test import APIClient

from apps.identity.tests.factories import UserFactory
from apps.invoices.models import Invoice
from apps.invoices.services import submit_invoice, update_invoice, verify_invoice
from apps.organizations.models import Organization, UserMembership
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


def test_status_change_increments_optimistic_version():
    user, issuer, buyer = invoice_data()
    invoice = Invoice.objects.create(
        issuer=issuer,
        buyer=buyer,
        number="status-1",
        amount=Decimal("10"),
        due_date=date.today(),
        created_by=user,
    )

    invoice = submit_invoice(invoice=invoice, actor=user)
    invoice = verify_invoice(invoice=invoice, actor=user)

    assert invoice.status == Invoice.Status.VERIFIED
    assert invoice.version == 3


def test_buyer_cannot_update_issuer_invoice():
    issuer_user, issuer, buyer = invoice_data()
    buyer_user = UserFactory()
    UserMembership.objects.create(
        user=issuer_user, organization=issuer, role="operator", scopes=["create_invoice"]
    )
    UserMembership.objects.create(
        user=buyer_user, organization=buyer, role="operator", scopes=["view_invoice"]
    )
    invoice = Invoice.objects.create(
        issuer=issuer,
        buyer=buyer,
        number="protected-1",
        amount=Decimal("10"),
        due_date=date.today(),
        created_by=issuer_user,
    )
    client = APIClient()
    client.force_authenticate(buyer_user)

    response = client.patch(
        f"/api/v1/invoices/{invoice.pk}",
        {"amount": "20.0000"},
        format="json",
        HTTP_IF_MATCH="1",
    )

    assert response.status_code == 403
    invoice.refresh_from_db()
    assert invoice.amount == Decimal("10")
