from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from common.errors import DomainError
from common.idempotency import begin_idempotent_request, complete_idempotent_request

from .models import Facility, FacilityReservation


@transaction.atomic
def create_facility(*, actor, data, correlation_id=""):
    facility = Facility.objects.create(**data)
    record_event(
        actor=actor,
        action="facility.create",
        obj=facility,
        before={},
        after={"limit": facility.limit, "expiry": facility.expiry},
        correlation_id=correlation_id,
    )
    return facility


@transaction.atomic
def reserve_facility(*, facility_id, amount, key, actor, correlation_id=""):
    amount = Decimal(amount)
    if amount <= 0:
        raise DomainError("invalid_reservation_amount", "مبلغ رزرو باید بیشتر از صفر باشد.")

    record, replay = begin_idempotent_request(
        actor=actor,
        operation="facility.reserve",
        key=key,
        payload={"facility_id": facility_id, "amount": str(amount)},
    )
    if replay:
        return record.response_payload

    facility = Facility.objects.select_for_update().get(pk=facility_id)
    if facility.expiry < timezone.localdate():
        raise DomainError("facility_expired", "تاریخ اعتبار این تسهیلات گذشته است.")
    if facility.available_amount < amount:
        raise DomainError("facility_limit_exceeded", "سقف اعتبار کافی نیست.")

    before = facility.utilized_amount
    facility.utilized_amount += amount
    facility.save(update_fields=("utilized_amount",))
    reservation = FacilityReservation.objects.create(
        facility=facility,
        amount=amount,
        idempotency_key=key,
        created_by=actor,
    )
    record_event(
        actor=actor,
        action="facility.reserve",
        obj=facility,
        before={"utilized_amount": before},
        after={"utilized_amount": facility.utilized_amount},
        correlation_id=correlation_id,
    )
    return complete_idempotent_request(
        record,
        {
            "reservation_id": reservation.pk,
            "utilized": str(facility.utilized_amount),
            "available": str(facility.available_amount),
        },
    )
