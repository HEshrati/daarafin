from django.conf import settings
from django.db import models

from apps.organizations.models import Organization


class OnboardingCase(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        SUBMITTED = "submitted", "ارسال‌شده"
        UNDER_REVIEW = "under_review", "در بررسی"
        NEED_CHANGES = "need_changes", "نیازمند اصلاح"
        APPROVED = "approved", "تأیید"
        REJECTED = "rejected", "رد"
        SUSPENDED = "suspended", "تعلیق"

    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="onboarding_cases"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_onboardings"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reviewed_onboardings",
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization",),
                condition=models.Q(
                    status__in=["draft", "submitted", "under_review", "need_changes", "approved"]
                ),
                name="one_active_onboarding_per_org",
            )
        ]
