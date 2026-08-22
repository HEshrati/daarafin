from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.facilities.models import Facility
from apps.facilities.services import reserve_facility
from apps.invoices.models import Invoice
from apps.invoices.services import mark_invoice_financed
from apps.organizations.models import BankAccount
from common.errors import DomainError
from common.idempotency import begin_idempotent_request, complete_idempotent_request
from common.permissions import ensure_maker_checker

from .models import (
    FinancingQuote,
    FinancingQuoteInvoice,
    FinancingQuoteLine,
    FinancingRequest,
    FinancingRequestHistory,
)
from .selectors import active_policy

CENT = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class QuoteResult:
    principal: Decimal
    financing_fee: Decimal
    platform_fee: Decimal
    net_amount: Decimal


def calculate_quote(*, principal, term_days: int, policy) -> QuoteResult:
    if isinstance(principal, float):
        raise TypeError("principal must be Decimal or a decimal string, not float")
    principal = Decimal(principal)
    if principal <= 0 or term_days <= 0:
        raise DomainError("invalid_quote_terms", "مبلغ و مدت تأمین مالی باید بیشتر از صفر باشند.")

    financing_fee = (principal * policy.annual_rate * Decimal(term_days) / Decimal(365)).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
    platform_fee = (principal * policy.platform_fee_rate + policy.platform_fee_flat).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
    net_amount = (principal - financing_fee - platform_fee).quantize(CENT, rounding=ROUND_HALF_UP)
    if net_amount <= 0:
        raise DomainError("nonpositive_quote_net", "کارمزدها از مبلغ درخواست بیشتر یا مساوی‌اند.")
    return QuoteResult(
        principal=principal.quantize(CENT, rounding=ROUND_HALF_UP),
        financing_fee=financing_fee,
        platform_fee=platform_fee,
        net_amount=net_amount,
    )


@transaction.atomic
def create_quote(*, actor, invoice_ids, amount, term_days, correlation_id=""):
    unique_ids = tuple(dict.fromkeys(invoice_ids))
    if not unique_ids:
        raise DomainError("invoice_required", "حداقل یک فاکتور برای قیمت‌گذاری لازم است.")
    invoices = list(
        Invoice.objects.select_for_update()
        .select_related("issuer", "buyer")
        .filter(pk__in=unique_ids)
        .order_by("pk")
    )
    if len(invoices) != len(unique_ids):
        raise DomainError("invoice_not_found", "یک یا چند فاکتور پیدا نشد.", status_code=404)
    if any(invoice.status != Invoice.Status.VERIFIED for invoice in invoices):
        raise DomainError("invoice_not_verified", "فقط فاکتور تأییدشده قابل قیمت‌گذاری است.")
    active_request_exists = FinancingRequest.objects.filter(
        quote__invoices__in=invoices,
        status__in=(
            FinancingRequest.Status.QUOTED,
            FinancingRequest.Status.REQUESTED,
            FinancingRequest.Status.APPROVED,
        ),
    ).exists()
    if active_request_exists:
        raise DomainError(
            "invoice_financing_in_progress",
            "برای یک یا چند فاکتور، درخواست تأمین مالی فعال وجود دارد.",
            status_code=409,
        )
    issuer_ids = {invoice.issuer_id for invoice in invoices}
    if len(issuer_ids) != 1:
        raise DomainError("mixed_invoice_issuers", "همه فاکتورها باید متعلق به یک صادرکننده باشند.")

    if isinstance(amount, float):
        raise TypeError("amount must be Decimal or a decimal string, not float")
    amount = Decimal(amount)
    total_invoice_amount = sum((invoice.amount for invoice in invoices), Decimal("0"))
    if amount > total_invoice_amount:
        raise DomainError("amount_exceeds_invoices", "مبلغ درخواست از جمع فاکتورها بیشتر است.")

    policy = active_policy()
    if policy is None:
        raise DomainError("active_policy_not_found", "سیاست فعال قیمت‌گذاری تعریف نشده است.")
    result = calculate_quote(principal=amount, term_days=term_days, policy=policy)
    quote = FinancingQuote.objects.create(
        policy=policy,
        principal=result.principal,
        term_days=term_days,
        financing_fee=result.financing_fee,
        platform_fee=result.platform_fee,
        net_amount=result.net_amount,
        expires_at=timezone.now() + timedelta(minutes=15),
        created_by=actor,
    )
    FinancingQuoteInvoice.objects.bulk_create(
        [FinancingQuoteInvoice(quote=quote, invoice=invoice) for invoice in invoices]
    )
    FinancingQuoteLine.objects.bulk_create(
        [
            FinancingQuoteLine(
                quote=quote, kind=FinancingQuoteLine.Kind.PRINCIPAL, amount=result.principal
            ),
            FinancingQuoteLine(
                quote=quote,
                kind=FinancingQuoteLine.Kind.FINANCING_FEE,
                amount=result.financing_fee,
            ),
            FinancingQuoteLine(
                quote=quote,
                kind=FinancingQuoteLine.Kind.PLATFORM_FEE,
                amount=result.platform_fee,
            ),
            FinancingQuoteLine(
                quote=quote, kind=FinancingQuoteLine.Kind.NET_AMOUNT, amount=result.net_amount
            ),
        ]
    )
    request = FinancingRequest.objects.create(
        quote=quote,
        invoice=invoices[0],
        requested_amount=result.principal,
        term=term_days,
        created_by=actor,
    )
    record_event(
        actor=actor,
        action="financing.quote.create",
        obj=quote,
        before={},
        after={
            "policy_version": policy.version,
            "principal": result.principal,
            "net_amount": result.net_amount,
            "request_id": request.pk,
        },
        correlation_id=correlation_id,
    )
    return quote


@transaction.atomic
def submit_request(*, request, facility_id, key, actor, correlation_id=""):
    locked = _locked_request(request.pk)
    record, replay = begin_idempotent_request(
        actor=actor,
        operation="financing.request.submit",
        key=key,
        payload={"request_id": locked.pk, "facility_id": facility_id},
    )
    if replay:
        return FinancingRequest.objects.get(pk=record.response_payload["request_id"])
    if locked.status != FinancingRequest.Status.QUOTED:
        raise DomainError("invalid_financing_status", "فقط قیمت پیشنهادی قابل ثبت درخواست است.")
    if locked.quote.expires_at <= timezone.now():
        raise DomainError("quote_expired", "اعتبار قیمت پیشنهادی به پایان رسیده است.")
    try:
        facility = Facility.objects.select_for_update().get(pk=facility_id)
    except Facility.DoesNotExist as exc:
        raise DomainError("facility_not_found", "خط اعتباری پیدا نشد.", status_code=404) from exc
    if facility.borrower_id != locked.invoice.issuer_id:
        raise DomainError(
            "facility_borrower_mismatch", "خط اعتباری متعلق به صادرکننده فاکتور نیست."
        )
    if facility.expiry < timezone.localdate():
        raise DomainError("facility_expired", "تاریخ اعتبار خط اعتباری گذشته است.")
    if facility.available_amount < locked.requested_amount:
        raise DomainError("facility_limit_exceeded", "سقف اعتبار کافی نیست.")

    locked.facility = facility
    _transition(
        request=locked,
        target=FinancingRequest.Status.REQUESTED,
        actor=actor,
        correlation_id=correlation_id,
        extra_update_fields=("facility",),
    )
    complete_idempotent_request(record, {"request_id": locked.pk, "status": locked.status})
    return locked


@transaction.atomic
def approve_request(*, request, key, actor, correlation_id=""):
    locked = _locked_request(request.pk)
    record, replay = begin_idempotent_request(
        actor=actor,
        operation="financing.request.approve",
        key=key,
        payload={"request_id": locked.pk},
    )
    if replay:
        return FinancingRequest.objects.get(pk=record.response_payload["request_id"])
    if locked.status != FinancingRequest.Status.REQUESTED:
        raise DomainError("invalid_financing_status", "فقط درخواست ثبت‌شده قابل تأیید است.")
    ensure_maker_checker(actor=actor, maker=locked.created_by)
    locked.approved_by = actor
    _transition(
        request=locked,
        target=FinancingRequest.Status.APPROVED,
        actor=actor,
        correlation_id=correlation_id,
        extra_update_fields=("approved_by",),
    )
    complete_idempotent_request(record, {"request_id": locked.pk, "status": locked.status})
    return locked


@transaction.atomic
def reject_request(*, request, reason, key, actor, correlation_id=""):
    locked = _locked_request(request.pk)
    record, replay = begin_idempotent_request(
        actor=actor,
        operation="financing.request.reject",
        key=key,
        payload={"request_id": locked.pk, "reason": reason},
    )
    if replay:
        return FinancingRequest.objects.get(pk=record.response_payload["request_id"])
    if locked.status != FinancingRequest.Status.REQUESTED:
        raise DomainError("invalid_financing_status", "فقط درخواست ثبت‌شده قابل رد است.")
    ensure_maker_checker(actor=actor, maker=locked.created_by)
    locked.rejection_reason = reason
    _transition(
        request=locked,
        target=FinancingRequest.Status.REJECTED,
        actor=actor,
        reason=reason,
        correlation_id=correlation_id,
        extra_update_fields=("rejection_reason",),
    )
    complete_idempotent_request(record, {"request_id": locked.pk, "status": locked.status})
    return locked


@transaction.atomic
def disburse_request(*, request, bank_account_id, key, actor, correlation_id=""):
    locked = _locked_request(request.pk)
    record, replay = begin_idempotent_request(
        actor=actor,
        operation="financing.request.disburse",
        key=key,
        payload={"request_id": locked.pk, "bank_account_id": bank_account_id},
    )
    if replay:
        return FinancingRequest.objects.get(pk=record.response_payload["request_id"])
    if locked.status != FinancingRequest.Status.APPROVED:
        raise DomainError("invalid_financing_status", "فقط درخواست تأییدشده قابل پرداخت است.")
    if locked.facility_id is None:
        raise DomainError("facility_required", "برای درخواست تأییدشده خط اعتباری ثبت نشده است.")
    try:
        bank_account = BankAccount.objects.get(
            pk=bank_account_id,
            organization_id=locked.invoice.issuer_id,
            is_active=True,
        )
    except BankAccount.DoesNotExist as exc:
        raise DomainError(
            "bank_account_not_found", "حساب بانکی فعال متعلق به متقاضی پیدا نشد.", status_code=404
        ) from exc

    reserve_facility(
        facility_id=locked.facility_id,
        amount=locked.requested_amount,
        key=f"financing:{locked.pk}:{key}",
        actor=actor,
        correlation_id=correlation_id,
    )
    for line in locked.quote.invoice_lines.select_related("invoice"):
        mark_invoice_financed(
            invoice=line.invoice,
            actor=actor,
            correlation_id=correlation_id,
        )
    locked.bank_account = bank_account
    _transition(
        request=locked,
        target=FinancingRequest.Status.DISBURSED,
        actor=actor,
        correlation_id=correlation_id,
        extra_update_fields=("bank_account",),
    )
    complete_idempotent_request(record, {"request_id": locked.pk, "status": locked.status})
    return locked


def _locked_request(request_id):
    return (
        FinancingRequest.objects.select_for_update(of=("self",))
        .select_related("quote", "invoice", "facility", "created_by")
        .get(pk=request_id)
    )


def _transition(*, request, target, actor, correlation_id, reason="", extra_update_fields=()):
    before = request.status
    request.status = target
    request.save(update_fields=("status", "updated_at", *extra_update_fields))
    FinancingRequestHistory.objects.create(
        request=request,
        from_status=before,
        to_status=target,
        changed_by=actor,
        reason=reason,
    )
    record_event(
        actor=actor,
        action=f"financing.request.{target}",
        obj=request,
        before={"status": before},
        after={"status": target},
        correlation_id=correlation_id,
    )
