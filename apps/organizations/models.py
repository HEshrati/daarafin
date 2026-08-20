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
    gln = models.CharField(max_length=32, blank=True, default="", db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    risk_tier = models.PositiveSmallIntegerField(default=1)
    company_type = models.CharField(max_length=64, blank=True, default="")
    country = models.CharField(max_length=64, blank=True, default="")
    province = models.CharField(max_length=64, blank=True, default="")
    county = models.CharField(max_length=64, blank=True, default="")
    city = models.CharField(max_length=64, blank=True, default="")
    address = models.TextField(blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    email = models.EmailField(blank=True, default="")


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


class OrganizationContact(models.Model):
    class Role(models.TextChoices):
        CEO = "ceo", "مدیرعامل"
        TECHNICAL = "technical", "مسئول فنی"
        OWNER = "owner", "مالک / رابط"
        OTHER = "other", "سایر"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="contacts"
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    full_name = models.CharField(max_length=255, blank=True, default="")
    national_id = models.CharField(max_length=20, blank=True, default="")
    mobile = models.CharField(max_length=32, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=("organization", "role")),
            models.Index(fields=("national_id",)),
        ]


class PharmacyProfile(models.Model):
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="pharmacy_profile"
    )
    university_name = models.CharField(max_length=255, blank=True, default="")
    service_type = models.CharField(max_length=64, blank=True, default="")
    pharmacy_type = models.CharField(max_length=128, blank=True, default="")
    customer_national_id = models.CharField(max_length=20, blank=True, default="")
    owner_name = models.CharField(max_length=255, blank=True, default="")
    responsible_national_id = models.CharField(max_length=20, blank=True, default="")
    founder_mobile = models.CharField(max_length=32, blank=True, default="")
    landline = models.CharField(max_length=32, blank=True, default="")


class DistributorBranch(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="branches"
    )
    gln = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=255, blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    province = models.CharField(max_length=64, blank=True, default="")
    county = models.CharField(max_length=64, blank=True, default="")
    city = models.CharField(max_length=64, blank=True, default="")
    address = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "gln"), name="unique_org_branch_gln"
            )
        ]
