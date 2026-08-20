from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.facilities.models import Facility
from apps.financing.models import FinancingRequest
from apps.financing.services import create_quote, submit_request
from apps.identity.tests.factories import UserFactory
from apps.invoices.models import Invoice
from apps.organizations.models import Organization, UserMembership
from apps.organizations.services import DEFAULT_ROLE_SCOPES

pytestmark = pytest.mark.django_db


def _setup_demo_triangle():
    maker = UserFactory(username="dash-maker")
    approver = UserFactory(username="dash-approver")
    finance_user = UserFactory(username="dash-finance")
    lender = Organization.objects.create(
        name="بانک داشبورد", type=Organization.Type.BANK, national_id="70000000001"
    )
    borrower = Organization.objects.create(
        name="تولیدکننده داشبورد",
        type=Organization.Type.MANUFACTURER,
        national_id="70000000002",
    )
    buyer = Organization.objects.create(
        name="داروخانه داشبورد", type=Organization.Type.PHARMACY, national_id="70000000003"
    )
    UserMembership.objects.create(
        user=maker,
        organization=borrower,
        role=UserMembership.Role.OWNER,
        scopes=DEFAULT_ROLE_SCOPES["owner"].copy(),
    )
    UserMembership.objects.create(
        user=approver,
        organization=lender,
        role=UserMembership.Role.APPROVER,
        scopes=DEFAULT_ROLE_SCOPES["approver"].copy(),
    )
    UserMembership.objects.create(
        user=finance_user,
        organization=lender,
        role=UserMembership.Role.BANK_FINANCE,
        scopes=DEFAULT_ROLE_SCOPES["bank_finance"].copy(),
    )
    facility = Facility.objects.create(
        lender=lender,
        borrower=borrower,
        limit=Decimal("5000.0000"),
        expiry=date.today() + timedelta(days=90),
    )
    invoice = Invoice.objects.create(
        issuer=borrower,
        buyer=buyer,
        number="DASH-1",
        amount=Decimal("1000.0000"),
        due_date=date.today() + timedelta(days=30),
        status=Invoice.Status.VERIFIED,
        created_by=maker,
    )
    quote = create_quote(
        actor=maker, invoice_ids=[invoice.pk], amount=Decimal("800.0000"), term_days=30
    )
    submit_request(
        request=quote.request,
        facility_id=facility.pk,
        actor=maker,
        key="dash-submit-1",
    )
    return maker, approver, finance_user


def test_me_includes_memberships():
    maker, _, _ = _setup_demo_triangle()
    client = APIClient()
    client.force_authenticate(maker)
    response = client.get(reverse("me"))
    assert response.status_code == 200
    assert len(response.data["memberships"]) == 1
    membership = response.data["memberships"][0]
    assert membership["role"] == UserMembership.Role.OWNER
    assert membership["organization"]["type"] == Organization.Type.MANUFACTURER


def test_dashboard_persona_payloads_for_demo_roles():
    maker, approver, finance_user = _setup_demo_triangle()
    client = APIClient()

    client.force_authenticate(maker)
    supplier = client.get("/api/v1/financing/dashboard")
    assert supplier.status_code == 200
    assert supplier.data["persona"] == "supplier"
    assert len(supplier.data["kpis"]) == 4
    assert len(supplier.data["charts"]) == 2
    assert supplier.data["table"]["title"]

    client.force_authenticate(approver)
    bank_approver = client.get("/api/v1/financing/dashboard")
    assert bank_approver.status_code == 200
    assert bank_approver.data["persona"] == "bank_approver"
    assert bank_approver.data["kpis"][0]["key"] == "queue_count"

    client.force_authenticate(finance_user)
    bank_finance = client.get("/api/v1/financing/dashboard")
    assert bank_finance.status_code == 200
    assert bank_finance.data["persona"] == "bank_finance"
    assert any(kpi["key"] == "ready_count" for kpi in bank_finance.data["kpis"])

    schema = client.get("/api/schema/", HTTP_ACCEPT="application/json")
    assert schema.status_code == 200
    assert "/api/v1/financing/dashboard" in schema.json()["paths"]
