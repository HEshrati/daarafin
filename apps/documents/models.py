from django.conf import settings
from django.db import models

from apps.onboarding.models import OnboardingCase


class Document(models.Model):
    class ScanStatus(models.TextChoices):
        PENDING = "pending", "در انتظار"
        CLEAN = "clean", "سالم"
        INFECTED = "infected", "آلوده"

    onboarding_case = models.ForeignKey(
        OnboardingCase, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(max_length=50)
    storage_key = models.CharField(max_length=500, unique=True)
    version = models.PositiveIntegerField(default=1)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    scan_status = models.CharField(
        max_length=10, choices=ScanStatus.choices, default=ScanStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("onboarding_case", "document_type", "version"),
                name="unique_document_version",
            )
        ]
