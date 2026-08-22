from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.exceptions import PermissionDenied

from apps.facilities.models import Facility
from apps.financing.models import FinancingQuoteLine, FinancingRequest, Policy
from apps.financing.services import (
    approve_request,
    calculate_quote,
    create_quote,
    disburse_request,
    submit_request,
)
from apps.identity.tests.factories import UserFactory
from apps.invoices.models import Invoice
from apps.organizations.models import BankAccount, Organization
from common.errors import DomainError

pytestmark = pytest.mark.django_db


def make_context():
    maker = UserFactory()
    approver = UserFactory()
    finance_user = UserFactory()
    lender = Organization.objects.create(
        name="بانک دمو", type=Organization.Type.BANK, national_id="50000000001"
    )
    borrower = Organization.objects.create(
        name="تولیدکننده دمو",
        type=Organization.Type.MANUFACTURER,
        national_id="50000000002",
    )
    buyer = Organization.objects.create(
        name="خریدار دمو", type=Organization.Type.PHARMACY, national_id="50000000003"
    )
    invoice = Invoice.objects.create(
        issuer=borrower,
        buyer=buyer,
        number="FIN-DEMO-1",
        amount=Decimal("1000.0000"),
        due_date=date.today() + timedelta(days=60),
        status=Invoice.Status.VERIFIED,
        created_by=maker,
    )
    facility = Facility.objects.create(
        lender=lender,
        borrower=borrower,
        limit=Decimal("2000.0000"),
        expiry=date.today() + timedelta(days=90),
    )
    bank_account = BankAccount.objects.create(
        organization=borrower,
        iban="IR000000000000000000000001",
    )
    return maker, approver, finance_user, lender, borrower, invoice, facility, bank_account


def test_calculate_quote_uses_half_up_and_rejects_float():
    policy = Policy(
        annual_rate=Decimal("0.000000"),
        platform_fee_rate=Decimal("0.000000"),
        platform_fee_flat=Decimal("0.0050"),
    )

    result = calculate_quote(principal=Decimal("10.0000"), term_days=30, policy=policy)

    assert result.platform_fee == Decimal("0.01")
    assert result.net_amount == Decimal("9.99")
    with pytest.raises(TypeError):
        calculate_quote(principal=10.0, term_days=30, policy=policy)


def test_create_quote_persists_policy_and_separate_lines():
    maker, _, _, _, _, invoice, _, _ = make_context()
    Policy.objects.filter(is_active=True).update(
        annual_rate=Decimal("0.240000"),
        platform_fee_rate=Decimal("0.010000"),
        platform_fee_flat=Decimal("0.0000"),
    )

    quote = create_quote(
        actor=maker,
        invoice_ids=[invoice.pk],
        amount=Decimal("600.0000"),
        term_days=30,
    )

    lines = {line.kind: line.amount for line in quote.lines.all()}
    assert quote.policy.version == 1
    assert quote.request.status == FinancingRequest.Status.QUOTED
    assert lines == {
        FinancingQuoteLine.Kind.PRINCIPAL: Decimal("600.0000"),
        FinancingQuoteLine.Kind.FINANCING_FEE: Decimal("11.8400"),
        FinancingQuoteLine.Kind.PLATFORM_FEE: Decimal("6.0000"),
        FinancingQuoteLine.Kind.NET_AMOUNT: Decimal("582.1600"),
    }


def test_only_verified_invoice_can_be_quoted():
    maker, _, _, _, _, invoice, _, _ = make_context()
    invoice.status = Invoice.Status.DRAFT
    invoice.save(update_fields=("status",))

    with pytest.raises(DomainError) as exc:
        create_quote(
            actor=maker,
            invoice_ids=[invoice.pk],
            amount=Decimal("500.0000"),
            term_days=30,
        )

    assert exc.value.get_codes()["code"] == "invoice_not_verified"


def test_invoice_cannot_have_multiple_active_financing_requests():
    maker, _, _, _, _, invoice, _, _ = make_context()
    create_quote(
        actor=maker,
        invoice_ids=[invoice.pk],
        amount=Decimal("500.0000"),
        term_days=30,
    )

    with pytest.raises(DomainError) as exc:
        create_quote(
            actor=maker,
            invoice_ids=[invoice.pk],
            amount=Decimal("400.0000"),
            term_days=30,
        )

    assert exc.value.get_codes()["code"] == "invoice_financing_in_progress"


def test_happy_path_is_idempotent_and_updates_facility_and_invoice():
    maker, approver, finance_user, _, _, invoice, facility, bank_account = make_context()
    quote = create_quote(
        actor=maker,
        invoice_ids=[invoice.pk],
        amount=Decimal("600.0000"),
        term_days=30,
    )
    request = quote.request

    submitted = submit_request(
        request=request,
        facility_id=facility.pk,
        key="submit-demo",
        actor=maker,
    )
    submitted_again = submit_request(
        request=request,
        facility_id=facility.pk,
        key="submit-demo",
        actor=maker,
    )
    approved = approve_request(
        request=submitted,
        key="approve-demo",
        actor=approver,
    )
    approved_again = approve_request(
        request=submitted,
        key="approve-demo",
        actor=approver,
    )
    disbursed = disburse_request(
        request=approved,
        bank_account_id=bank_account.pk,
        key="disburse-demo",
        actor=finance_user,
    )
    disbursed_again = disburse_request(
        request=approved,
        bank_account_id=bank_account.pk,
        key="disburse-demo",
        actor=finance_user,
    )

    invoice.refresh_from_db()
    facility.refresh_from_db()
    disbursed.refresh_from_db()
    assert submitted.pk == submitted_again.pk
    assert approved.pk == approved_again.pk
    assert disbursed.pk == disbursed_again.pk
    assert disbursed.status == FinancingRequest.Status.DISBURSED
    assert invoice.status == Invoice.Status.FINANCED
    assert facility.utilized_amount == Decimal("600.0000")
    assert list(disbursed.history.values_list("to_status", flat=True)) == [
        FinancingRequest.Status.REQUESTED,
        FinancingRequest.Status.APPROVED,
        FinancingRequest.Status.DISBURSED,
    ]


def test_maker_cannot_approve_own_request():
    maker, _, _, _, _, invoice, facility, _ = make_context()
    quote = create_quote(
        actor=maker,
        invoice_ids=[invoice.pk],
        amount=Decimal("500.0000"),
        term_days=30,
    )
    request = submit_request(
        request=quote.request,
        facility_id=facility.pk,
        key="submit-maker-checker",
        actor=maker,
    )

    with pytest.raises(PermissionDenied):
        approve_request(
            request=request,
            key="approve-maker-checker",
            actor=maker,
        )


def test_invalid_direct_disbursement_does_not_reserve_facility():
    maker, _, finance_user, _, _, invoice, facility, bank_account = make_context()
    quote = create_quote(
        actor=maker,
        invoice_ids=[invoice.pk],
        amount=Decimal("500.0000"),
        term_days=30,
    )
    request = submit_request(
        request=quote.request,
        facility_id=facility.pk,
        key="submit-no-direct-disburse",
        actor=maker,
    )

    with pytest.raises(DomainError) as exc:
        disburse_request(
            request=request,
            bank_account_id=bank_account.pk,
            key="no-direct-disburse",
            actor=finance_user,
        )

    facility.refresh_from_db()
    assert exc.value.get_codes()["code"] == "invalid_financing_status"
    assert facility.utilized_amount == Decimal("0.0000")
