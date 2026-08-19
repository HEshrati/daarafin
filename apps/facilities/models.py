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

    @property
    def available_amount(self):
        return self.limit - self.utilized_amount


class FacilityReservation(models.Model):
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="reservations")
    amount = models.DecimalField(max_digits=24, decimal_places=4)
    idempotency_key = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
