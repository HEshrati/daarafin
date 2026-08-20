from django.conf import settings
from django.db import models

from apps.facilities.models import Facility
from apps.invoices.models import Invoice
from apps.organizations.models import BankAccount


class Policy(models.Model):
    version = models.PositiveIntegerField(unique=True)
    annual_rate = models.DecimalField(max_digits=9, decimal_places=6)
    platform_fee_rate = models.DecimalField(max_digits=9, decimal_places=6)
    platform_fee_flat = models.DecimalField(max_digits=24, decimal_places=4, default=0)
    effective_from = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "policies"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(annual_rate__gte=0), name="policy_annual_rate_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(platform_fee_rate__gte=0),
                name="policy_platform_rate_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(platform_fee_flat__gte=0),
                name="policy_platform_flat_nonnegative",
            ),
            models.UniqueConstraint(
                fields=("is_active",),
                condition=models.Q(is_active=True),
                name="unique_active_financing_policy",
            ),
        ]


class FinancingQuote(models.Model):
    policy = models.ForeignKey(Policy, on_delete=models.PROTECT, related_name="quotes")
    invoices = models.ManyToManyField(
        Invoice, through="FinancingQuoteInvoice", related_name="financing_quotes"
    )
    principal = models.DecimalField(max_digits=24, decimal_places=4)
    term_days = models.PositiveIntegerField()
    financing_fee = models.DecimalField(max_digits=24, decimal_places=4)
    platform_fee = models.DecimalField(max_digits=24, decimal_places=4)
    net_amount = models.DecimalField(max_digits=24, decimal_places=4)
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(principal__gt=0), name="financing_quote_principal_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(term_days__gt=0), name="financing_quote_term_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(financing_fee__gte=0),
                name="financing_quote_fee_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(platform_fee__gte=0),
                name="financing_quote_platform_fee_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(net_amount__gt=0), name="financing_quote_net_positive"
            ),
        ]


class FinancingQuoteInvoice(models.Model):
    quote = models.ForeignKey(
        FinancingQuote, on_delete=models.CASCADE, related_name="invoice_lines"
    )
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("quote", "invoice"), name="unique_invoice_per_financing_quote"
            )
        ]


class FinancingQuoteLine(models.Model):
    class Kind(models.TextChoices):
        PRINCIPAL = "principal", "اصل مبلغ"
        FINANCING_FEE = "financing_fee", "هزینه تأمین مالی"
        PLATFORM_FEE = "platform_fee", "کارمزد پلتفرم"
        NET_AMOUNT = "net_amount", "مبلغ خالص"

    quote = models.ForeignKey(FinancingQuote, on_delete=models.CASCADE, related_name="lines")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    amount = models.DecimalField(max_digits=24, decimal_places=4)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("quote", "kind"), name="unique_kind_per_financing_quote"
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gte=0), name="financing_quote_line_nonnegative"
            ),
        ]


class FinancingRequest(models.Model):
    class Status(models.TextChoices):
        QUOTED = "quoted", "قیمت‌گذاری‌شده"
        REQUESTED = "requested", "درخواست‌شده"
        APPROVED = "approved", "تأییدشده"
        REJECTED = "rejected", "ردشده"
        DISBURSED = "disbursed", "پرداخت‌شده"

    quote = models.OneToOneField(FinancingQuote, on_delete=models.PROTECT, related_name="request")
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="financing_requests"
    )
    facility = models.ForeignKey(
        Facility, null=True, blank=True, on_delete=models.PROTECT, related_name="financing_requests"
    )
    bank_account = models.ForeignKey(
        BankAccount,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="financing_requests",
    )
    requested_amount = models.DecimalField(max_digits=24, decimal_places=4)
    term = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUOTED)
    rejection_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_financing_requests",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approved_financing_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=("status", "created_at"))]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(requested_amount__gt=0),
                name="financing_request_amount_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(term__gt=0), name="financing_request_term_positive"
            ),
        ]


class FinancingRequestHistory(models.Model):
    request = models.ForeignKey(FinancingRequest, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=16, choices=FinancingRequest.Status.choices)
    to_status = models.CharField(max_length=16, choices=FinancingRequest.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
