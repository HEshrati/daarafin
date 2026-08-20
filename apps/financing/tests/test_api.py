from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.facilities.models import Facility
from apps.identity.tests.factories import UserFactory
from apps.invoices.models import Invoice
from apps.organizations.models import Organization, UserMembership

pytestmark = pytest.mark.django_db


def test_quote_endpoint_is_documented_and_requires_verified_visible_invoice():
    maker = UserFactory()
    lender = Organization.objects.create(
        name="بانک API", type=Organization.Type.BANK, national_id="60000000001"
    )
    borrower = Organization.objects.create(
        name="متقاضی API", type=Organization.Type.MANUFACTURER, national_id="60000000002"
    )
    buyer = Organization.objects.create(
        name="خریدار API", type=Organization.Type.PHARMACY, national_id="60000000003"
    )
    UserMembership.objects.create(
        user=maker,
        organization=borrower,
        role=UserMembership.Role.OPERATOR,
        scopes=["view_invoice", "create_financing", "view_financing"],
    )
    invoice = Invoice.objects.create(
        issuer=borrower,
        buyer=buyer,
        number="API-FIN-1",
        amount=Decimal("800.0000"),
        due_date=date.today() + timedelta(days=30),
        status=Invoice.Status.VERIFIED,
        created_by=maker,
    )
    Facility.objects.create(
        lender=lender,
        borrower=borrower,
        limit=Decimal("1000.0000"),
        expiry=date.today() + timedelta(days=60),
    )
    client = APIClient()
    client.force_authenticate(maker)

    response = client.post(
        "/api/v1/financing/quotes",
        {"invoice_ids": [invoice.pk], "amount": "500.0000", "term": 30},
        format="json",
    )
    schema = client.get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 201
    assert response.data["policy_version"] == 1
    assert len(response.data["lines"]) == 4
    assert schema.status_code == 200
    assert "/api/v1/financing/quotes" in schema.json()["paths"]
    assert "/api/v1/financing/{id}/approve" in schema.json()["paths"]
