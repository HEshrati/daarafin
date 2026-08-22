from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.facilities.models import Facility
from apps.facilities.services import create_facility, reserve_facility
from apps.identity.tests.factories import UserFactory
from apps.organizations.models import Organization
from common.errors import DomainError

pytestmark = pytest.mark.django_db(transaction=True)


def make_facility():
    lender = Organization.objects.create(name="بانک", type="bank", national_id="33333333333")
    borrower = Organization.objects.create(
        name="شرکت", type="manufacturer", national_id="44444444444"
    )
    return Facility.objects.create(
        lender=lender,
        borrower=borrower,
        limit=Decimal("100"),
        expiry=date.today() + timedelta(days=30),
    )


def test_reservation_is_idempotent():
    f = make_facility()
    actor = UserFactory()
    first = reserve_facility(facility_id=f.pk, amount="60", key="same", actor=actor)
    second = reserve_facility(facility_id=f.pk, amount="60", key="same", actor=actor)
    f.refresh_from_db()
    assert first == second and f.utilized_amount == Decimal("60")


def test_reservation_cannot_exceed_limit():
    f = make_facility()
    actor = UserFactory()
    reserve_facility(facility_id=f.pk, amount="80", key="one", actor=actor)
    with pytest.raises(DomainError):
        reserve_facility(facility_id=f.pk, amount="30", key="two", actor=actor)


def test_idempotency_key_cannot_be_reused_with_different_amount():
    facility = make_facility()
    actor = UserFactory()
    reserve_facility(facility_id=facility.pk, amount="10", key="same-key", actor=actor)

    with pytest.raises(DomainError) as exc:
        reserve_facility(facility_id=facility.pk, amount="11", key="same-key", actor=actor)

    assert exc.value.get_codes()["code"] == "idempotency_key_reused"


def test_expired_facility_cannot_be_reserved():
    facility = make_facility()
    facility.expiry = date.today() - timedelta(days=1)
    facility.save(update_fields=("expiry",))

    with pytest.raises(DomainError):
        reserve_facility(
            facility_id=facility.pk,
            amount="10",
            key="expired",
            actor=UserFactory(),
        )


def test_facility_lender_must_be_a_bank():
    lender = Organization.objects.create(
        name="تولیدکننده اعتباردهنده",
        type=Organization.Type.MANUFACTURER,
        national_id="55555555551",
    )
    borrower = Organization.objects.create(
        name="تولیدکننده اعتبارگیرنده",
        type=Organization.Type.MANUFACTURER,
        national_id="55555555552",
    )

    with pytest.raises(DomainError) as exc:
        create_facility(
            actor=UserFactory(),
            data={
                "lender": lender,
                "borrower": borrower,
                "limit": Decimal("100"),
                "expiry": date.today() + timedelta(days=30),
            },
        )

    assert exc.value.get_codes()["code"] == "invalid_facility_lender"
