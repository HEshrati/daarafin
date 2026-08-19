from django.db import IntegrityError, transaction

from apps.audit.services import record_event
from common.errors import DomainError
from common.idempotency import begin_idempotent_request, complete_idempotent_request

from .models import Invoice, InvoiceDispute

FINAL_STATUSES = {Invoice.Status.FINANCED, Invoice.Status.SETTLED}


@transaction.atomic
def create_invoice(*, actor, data, correlation_id=""):
    try:
        with transaction.atomic():
            invoice = Invoice.objects.create(created_by=actor, **data)
    except IntegrityError as exc:
        raise DomainError(
            "duplicate_or_invalid_invoice",
            "شماره فاکتور تکراری است یا اطلاعات فاکتور معتبر نیست.",
            status_code=409,
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
def update_invoice(*, invoice, actor, data, expected_version, correlation_id=""):
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if locked.version != expected_version:
        raise DomainError(
            "version_conflict", "رکورد توسط کاربر دیگری تغییر کرده است.", status_code=409
        )
    if locked.status in FINAL_STATUSES:
        raise DomainError("immutable_invoice", "فاکتور تأمین/تسویه‌شده قابل ویرایش نیست.")

    before = {
        field: getattr(locked, field)
        for field in ("issuer_id", "buyer_id", "number", "amount", "due_date", "version")
    }
    for key, value in data.items():
        setattr(locked, key, value)
    locked.version += 1
    try:
        with transaction.atomic():
            locked.save()
    except IntegrityError as exc:
        raise DomainError(
            "duplicate_or_invalid_invoice",
            "شماره فاکتور تکراری است یا اطلاعات فاکتور معتبر نیست.",
            status_code=409,
        ) from exc
    record_event(
        actor=actor,
        action="invoice.update",
        obj=locked,
        before=before,
        after={**before, **data, "version": locked.version},
        correlation_id=correlation_id,
    )
    return locked


@transaction.atomic
def delete_invoice(*, invoice, actor, correlation_id=""):
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if locked.status in FINAL_STATUSES:
        raise DomainError("immutable_invoice", "فاکتور تأمین/تسویه‌شده قابل حذف نیست.")
    record_event(
        actor=actor,
        action="invoice.delete",
        obj=locked,
        before={"status": locked.status, "amount": locked.amount},
        after={},
        correlation_id=correlation_id,
    )
    locked.delete()


@transaction.atomic
def submit_invoice(*, invoice, actor, correlation_id=""):
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if locked.status != Invoice.Status.DRAFT:
        raise DomainError("invalid_invoice_status", "فقط فاکتور پیش‌نویس قابل ارسال است.")
    return _change_status(
        invoice=locked,
        actor=actor,
        target=Invoice.Status.SUBMITTED,
        action="invoice.submit",
        correlation_id=correlation_id,
    )


@transaction.atomic
def verify_invoice(*, invoice, actor, correlation_id=""):
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if locked.status != Invoice.Status.SUBMITTED:
        raise DomainError("invalid_invoice_status", "فقط فاکتور ارسال‌شده قابل تأیید است.")
    return _change_status(
        invoice=locked,
        actor=actor,
        target=Invoice.Status.VERIFIED,
        action="invoice.verify",
        correlation_id=correlation_id,
    )


@transaction.atomic
def dispute_invoice(*, invoice, actor, reason, attachment=None, correlation_id=""):
    locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if locked.status not in {Invoice.Status.SUBMITTED, Invoice.Status.VERIFIED}:
        raise DomainError(
            "invalid_invoice_status", "فقط فاکتور ارسال‌شده یا تأییدشده قابل اعتراض است."
        )
    before = locked.status
    locked.status = Invoice.Status.DISPUTED
    locked.version += 1
    locked.save(update_fields=("status", "version"))
    InvoiceDispute.objects.create(
        invoice=locked, reason=reason, attachment=attachment, created_by=actor
    )
    record_event(
        actor=actor,
        action="invoice.dispute",
        obj=locked,
        before={"status": before},
        after={"status": locked.status},
        correlation_id=correlation_id,
    )
    return locked


def _change_status(*, invoice, actor, target, action, correlation_id):
    before = invoice.status
    invoice.status = target
    invoice.version += 1
    invoice.save(update_fields=("status", "version"))
    record_event(
        actor=actor,
        action=action,
        obj=invoice,
        before={"status": before},
        after={"status": invoice.status},
        correlation_id=correlation_id,
    )
    return invoice


@transaction.atomic
def bulk_commit(*, actor, rows, key, correlation_id=""):
    payload_rows = [
        {
            "issuer": row["issuer"].pk,
            "buyer": row["buyer"].pk,
            "number": row["number"],
            "amount": str(row["amount"]),
            "due_date": row["due_date"].isoformat(),
        }
        for row in rows
    ]
    record, replay = begin_idempotent_request(
        actor=actor,
        operation="invoice.bulk_commit",
        key=key,
        payload={"rows": payload_rows},
    )
    if replay:
        return record.response_payload

    created = [
        create_invoice(actor=actor, data=row, correlation_id=correlation_id).pk for row in rows
    ]
    return complete_idempotent_request(record, {"invoice_ids": created})
