from django.conf import settings
from django.db import models

from apps.documents.models import Document
from apps.organizations.models import Organization


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        SUBMITTED = "submitted", "ارسال"
        VERIFIED = "verified", "تأیید"
        DISPUTED = "disputed", "اختلاف"
        FINANCED = "financed", "تأمین"
        SETTLED = "settled", "تسویه"

    issuer = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="issued_invoices"
    )
    buyer = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="bought_invoices"
    )
    number = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=24, decimal_places=4)
    due_date = models.DateField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("issuer", "number"), name="unique_issuer_invoice_number"
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="invoice_amount_positive"
            ),
            models.CheckConstraint(
                condition=~models.Q(issuer=models.F("buyer")), name="invoice_parties_differ"
            ),
        ]
        indexes = [models.Index(fields=("buyer", "status", "due_date"))]


class InvoiceDispute(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="disputes")
    reason = models.TextField()
    attachment = models.ForeignKey(Document, null=True, blank=True, on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
