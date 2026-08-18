from django.conf import settings
from django.db import models


class Organization(models.Model):
    class Type(models.TextChoices):
        BANK = "bank", "بانک"
        INSURANCE = "insurance", "بیمه"
        MANUFACTURER = "manufacturer", "تولیدکننده"
        DISTRIBUTOR = "distributor", "پخش"
        PHARMACY = "pharmacy", "داروخانه"

    class Status(models.TextChoices):
        ACTIVE = "active", "فعال"
        SUSPENDED = "suspended", "معلق"

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=Type.choices)
    national_id = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    risk_tier = models.PositiveSmallIntegerField(default=1)


class UserMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "مالک سازمان"
        OPERATOR = "operator", "اپراتور"
        APPROVER = "approver", "تأییدکننده"
        RISK_EXPERT = "risk_expert", "کارشناس ریسک"
        BANK_FINANCE = "bank_finance", "مالی بانک"
        SUPPORT = "support", "پشتیبان"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    scopes = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "organization", "role"), name="unique_user_org_role"
            )
        ]


class BankAccount(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="bank_accounts"
    )
    iban = models.CharField(max_length=26)
    is_active = models.BooleanField(default=True)
