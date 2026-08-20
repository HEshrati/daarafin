from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.facilities.models import Facility
from apps.financing.services import create_quote, submit_request
from apps.identity.tests.factories import UserFactory
from apps.invoices.models import Invoice
from apps.organizations.models import Organization, UserMembership
from apps.organizations.services import DEFAULT_ROLE_SCOPES

pytestmark = pytest.mark.django_db


def _membership(user, organization, role):
    return UserMembership.objects.create(
        user=user,
        organization=organization,
        role=role,
        scopes=DEFAULT_ROLE_SCOPES[role].copy(),
    )


def _setup_chain():
    maker = UserFactory(username="dash-maker")
    distributor_user = UserFactory(username="dash-distributor")
    pharmacy_user = UserFactory(username="dash-pharmacy")
    approver = UserFactory(username="dash-approver")
    finance_user = UserFactory(username="dash-finance")

    lender = Organization.objects.create(
        name="بانک داشبورد", type=Organization.Type.BANK, national_id="70000000001"
    )
    manufacturer = Organization.objects.create(
        name="تولیدکننده داشبورد",
        type=Organization.Type.MANUFACTURER,
        national_id="70000000002",
    )
    distributor = Organization.objects.create(
        name="پخش داشبورد", type=Organization.Type.DISTRIBUTOR, national_id="70000000004"
    )
    pharmacy = Organization.objects.create(
        name="داروخانه داشبورد", type=Organization.Type.PHARMACY, national_id="70000000003"
    )

    _membership(maker, manufacturer, UserMembership.Role.OWNER)
    _membership(distributor_user, distributor, UserMembership.Role.OWNER)
    _membership(pharmacy_user, pharmacy, UserMembership.Role.OWNER)
    _membership(approver, lender, UserMembership.Role.APPROVER)
    _membership(finance_user, lender, UserMembership.Role.BANK_FINANCE)

    facility = Facility.objects.create(
        lender=lender,
        borrower=manufacturer,
        limit=Decimal("5000.0000"),
        expiry=date.today() + timedelta(days=90),
    )
    invoice = Invoice.objects.create(
        issuer=manufacturer,
        buyer=pharmacy,
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

    dist_facility = Facility.objects.create(
        lender=lender,
        borrower=distributor,
        limit=Decimal("3000.0000"),
        expiry=date.today() + timedelta(days=90),
    )
    dist_invoice = Invoice.objects.create(
        issuer=distributor,
        buyer=pharmacy,
        number="DASH-DIST-1",
        amount=Decimal("600.0000"),
        due_date=date.today() + timedelta(days=30),
        status=Invoice.Status.VERIFIED,
        created_by=distributor_user,
    )
    dist_quote = create_quote(
        actor=distributor_user,
        invoice_ids=[dist_invoice.pk],
        amount=Decimal("500.0000"),
        term_days=30,
    )
    submit_request(
        request=dist_quote.request,
        facility_id=dist_facility.pk,
        actor=distributor_user,
        key="dash-submit-dist-1",
    )

    return maker, distributor_user, pharmacy_user, approver, finance_user


def test_me_includes_memberships():
    maker, *_ = _setup_chain()
    client = APIClient()
    client.force_authenticate(maker)
    response = client.get(reverse("me"))
    assert response.status_code == 200
    assert len(response.data["memberships"]) == 1
    membership = response.data["memberships"][0]
    assert membership["role"] == UserMembership.Role.OWNER
    assert membership["organization"]["type"] == Organization.Type.MANUFACTURER


def test_dashboard_persona_payloads_for_chain_and_bank_roles():
    maker, distributor_user, pharmacy_user, approver, finance_user = _setup_chain()
    client = APIClient()

    cases = [
        (maker, "supplier"),
        (distributor_user, "distributor"),
        (pharmacy_user, "pharmacy"),
        (approver, "bank_approver"),
        (finance_user, "bank_finance"),
    ]
    for user, persona in cases:
        client.force_authenticate(user)
        response = client.get("/api/v1/financing/dashboard")
        assert response.status_code == 200, persona
        assert response.data["persona"] == persona
        assert len(response.data["kpis"]) == 4
        assert len(response.data["charts"]) == 2

    schema = client.get("/api/schema/", HTTP_ACCEPT="application/json")
    assert schema.status_code == 200
    assert "/api/v1/financing/dashboard" in schema.json()["paths"]
