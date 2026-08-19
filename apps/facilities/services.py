from decimal import Decimal

from django.db import transaction

from common.errors import DomainError
from common.idempotency import IdempotencyRecord

from .models import Facility, FacilityReservation


@transaction.atomic
def reserve_facility(*, facility_id, amount, key):
    if not key:
        raise DomainError("idempotency_key_required", "هدر Idempotency-Key الزامی است.")
    previous = IdempotencyRecord.objects.filter(key=key).first()
    if previous:
        return previous.response_payload
    facility = Facility.objects.select_for_update().get(pk=facility_id)
    amount = Decimal(amount)
    if facility.available_amount < amount:
        raise DomainError("facility_limit_exceeded", "سقف اعتبار کافی نیست.")
    facility.utilized_amount += amount
    facility.save(update_fields=("utilized_amount",))
    reservation = FacilityReservation.objects.create(
        facility=facility, amount=amount, idempotency_key=key
    )
    payload = {
        "reservation_id": reservation.pk,
        "utilized": str(facility.utilized_amount),
        "available": str(facility.available_amount),
    }
    IdempotencyRecord.objects.create(key=key, response_payload=payload)
    return payload
