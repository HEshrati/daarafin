from django.conf import settings
from django.db import models

from apps.organizations.models import Organization


class Facility(models.Model):
    lender = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="lent_facilities"
    )
    borrower = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="borrowed_facilities"
    )
    limit = models.DecimalField(max_digits=24, decimal_places=4)
    utilized_amount = models.DecimalField(max_digits=24, decimal_places=4, default=0)
    expiry = models.DateField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(limit__gt=0), name="facility_limit_positive"),
            models.CheckConstraint(
                condition=models.Q(utilized_amount__gte=0), name="facility_utilized_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(utilized_amount__lte=models.F("limit")),
                name="facility_utilized_within_limit",
            ),
            models.CheckConstraint(
                condition=~models.Q(lender=models.F("borrower")), name="facility_parties_differ"
            ),
        ]

    @property
    def available_amount(self):
        return self.limit - self.utilized_amount


class FacilityReservation(models.Model):
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="reservations")
    amount = models.DecimalField(max_digits=24, decimal_places=4)
    idempotency_key = models.CharField(max_length=255)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("facility", "created_by", "idempotency_key"),
                name="unique_facility_reservation_key",
            )
        ]
