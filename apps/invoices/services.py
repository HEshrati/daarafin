from django.db import IntegrityError, transaction

from apps.audit.services import record_event
from common.errors import DomainError
from common.idempotency import IdempotencyRecord

from .models import Invoice, InvoiceDispute


@transaction.atomic
def create_invoice(*, actor, data, correlation_id=""):
    try:
        invoice = Invoice.objects.create(created_by=actor, **data)
    except IntegrityError as exc:
        raise DomainError(
            "duplicate_invoice", "شماره فاکتور برای صادرکننده تکراری است.", status_code=409
        ) from exc
    record_event(
        actor=actor,
        action="invoice.create",
        obj=invoice,
        before={},
        after={"status": invoice.status, "amount": invoice.amount},
        correlation_id=correlation_id,
    )
    return invoice


@transaction.atomic
def update_invoice(*, invoice, actor, data, expected_version):
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if locked.version != expected_version:
        raise DomainError("version_conflict", "رکورد توسط کاربر دیگری تغییر کرده", status_code=409)
    if locked.status in {"financed", "settled"}:
        raise DomainError("immutable_invoice", "فاکتور تأمین/تسویه‌شده قابل ویرایش نیست.")
    for key, value in data.items():
        setattr(locked, key, value)
    locked.version += 1
    locked.save()
    return locked


def delete_invoice(*, invoice):
    if invoice.status in {"financed", "settled"}:
        raise DomainError("immutable_invoice", "فاکتور تأمین/تسویه‌شده قابل حذف نیست.")
    invoice.delete()


def verify_invoice(*, invoice, actor, correlation_id=""):
    if invoice.status != "submitted":
        raise DomainError("invalid_invoice_status", "فقط فاکتور ارسال‌شده قابل تأیید است.")
    before = invoice.status
    invoice.status = "verified"
    invoice.save(update_fields=("status",))
    record_event(
        actor=actor,
        action="invoice.verify",
        obj=invoice,
        before={"status": before},
        after={"status": invoice.status},
        correlation_id=correlation_id,
    )
    return invoice


def dispute_invoice(*, invoice, actor, reason, attachment=None, correlation_id=""):
    before = invoice.status
    invoice.status = "disputed"
    invoice.save(update_fields=("status",))
    InvoiceDispute.objects.create(
        invoice=invoice, reason=reason, attachment=attachment, created_by=actor
    )
    record_event(
        actor=actor,
        action="invoice.dispute",
        obj=invoice,
        before={"status": before},
        after={"status": invoice.status},
        correlation_id=correlation_id,
    )
    return invoice


@transaction.atomic
def bulk_commit(*, actor, rows, key):
    if not key:
        raise DomainError("idempotency_key_required", "هدر Idempotency-Key الزامی است.")
    existing = IdempotencyRecord.objects.filter(key=key).first()
    if existing:
        return existing.response_payload
    created = [create_invoice(actor=actor, data=row).pk for row in rows]
    payload = {"invoice_ids": created}
    IdempotencyRecord.objects.create(key=key, response_payload=payload)
    return payload
