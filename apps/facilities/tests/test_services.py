from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.facilities.models import Facility
from apps.facilities.services import reserve_facility
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
    first = reserve_facility(facility_id=f.pk, amount="60", key="same")
    second = reserve_facility(facility_id=f.pk, amount="60", key="same")
    f.refresh_from_db()
    assert first == second and f.utilized_amount == Decimal("60")


def test_reservation_cannot_exceed_limit():
    f = make_facility()
    reserve_facility(facility_id=f.pk, amount="80", key="one")
    with pytest.raises(DomainError):
        reserve_facility(facility_id=f.pk, amount="30", key="two")
