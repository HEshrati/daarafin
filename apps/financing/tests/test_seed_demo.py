import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.facilities.models import Facility
from apps.financing.models import FinancingRequest
from apps.identity.models import User
from apps.invoices.models import Invoice
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


def test_seed_demo_is_idempotent_and_builds_lifecycle():
    call_command("seed_demo", password="test-demo-password")
    call_command("seed_demo", password="test-demo-password")

    assert User.objects.filter(username__startswith="demo-").count() == 5
    assert Invoice.objects.filter(number__startswith="DF-DEMO-").count() == 13
    assert Facility.objects.count() == 2
    assert Organization.objects.filter(type=Organization.Type.INSURANCE).count() == 4
    assert set(FinancingRequest.objects.values_list("status", flat=True)) == {
        FinancingRequest.Status.REQUESTED,
        FinancingRequest.Status.APPROVED,
        FinancingRequest.Status.DISBURSED,
    }

    client = APIClient()
    client.force_authenticate(User.objects.get(username="demo-approver"))
    approver_rows = client.get("/api/v1/financing/requests").data
    requested = next(row for row in approver_rows if row["status"] == "requested")
    assert set(requested["allowed_actions"]) == {"approve", "reject"}

    client.force_authenticate(User.objects.get(username="demo-finance"))
    finance_rows = client.get("/api/v1/financing/requests").data
    approved = next(row for row in finance_rows if row["status"] == "approved")
    assert approved["allowed_actions"] == ["disburse"]

    client.force_authenticate(User.objects.get(username="demo-maker"))
    insurers = client.get("/api/v1/organizations", {"type": "insurance"})
    assert insurers.status_code == 200
    assert len(insurers.data) == 4

    invoices = client.get("/api/v1/invoices")
    assert invoices.status_code == 200
    invoice_rows = invoices.data["results"] if isinstance(invoices.data, dict) else invoices.data
    assert len(invoice_rows) == 9
