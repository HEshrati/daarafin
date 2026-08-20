from datetime import date, timedelta
from decimal import Decimal

from django.db import models
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from apps.facilities.models import Facility
from apps.organizations.models import Organization, UserMembership

from .models import FinancingRequest, Policy

STATUS_LABELS = {
    FinancingRequest.Status.QUOTED: "قیمت‌گذاری‌شده",
    FinancingRequest.Status.REQUESTED: "در انتظار تأیید",
    FinancingRequest.Status.APPROVED: "تأییدشده",
    FinancingRequest.Status.REJECTED: "ردشده",
    FinancingRequest.Status.DISBURSED: "پرداخت‌شده",
}

PERSONA_SUPPLIER = "supplier"
PERSONA_BANK_APPROVER = "bank_approver"
PERSONA_BANK_FINANCE = "bank_finance"


def active_policy():
    return (
        Policy.objects.filter(is_active=True, effective_from__lte=timezone.now())
        .order_by("-effective_from", "-version")
        .first()
    )


def financing_requests_for_user(user):
    queryset = FinancingRequest.objects.select_related(
        "quote__policy",
        "invoice__issuer",
        "invoice__buyer",
        "facility__lender",
        "facility__borrower",
        "bank_account",
        "created_by",
        "approved_by",
    ).prefetch_related(
        "invoice__issuer__bank_accounts", "quote__invoice_lines", "quote__lines", "history"
    )
    if user.is_staff:
        return queryset

    organization_ids = [
        organization_id
        for organization_id, scopes in user.memberships.filter(is_active=True).values_list(
            "organization_id", "scopes"
        )
        if "view_financing" in scopes
    ]
    return queryset.filter(
        models.Q(invoice__issuer_id__in=organization_ids)
        | models.Q(facility__lender_id__in=organization_ids)
    ).distinct()


def _dec(value) -> str:
    if value is None:
        return "0"
    if isinstance(value, Decimal):
        return format(value.quantize(Decimal("0.0001")), "f")
    return str(value)


def _kpi(key: str, label: str, value, unit: str = "IRR") -> dict:
    return {"key": key, "label": label, "value": _dec(value) if unit == "IRR" else str(value), "unit": unit}


def resolve_dashboard_persona(user) -> tuple[str | None, UserMembership | None]:
    memberships = list(
        UserMembership.objects.filter(user=user, is_active=True)
        .select_related("organization")
        .order_by("id")
    )
    if not memberships:
        return None, None

    for membership in memberships:
        org = membership.organization
        if (
            org.type == Organization.Type.BANK
            and membership.role == UserMembership.Role.BANK_FINANCE
        ):
            return PERSONA_BANK_FINANCE, membership
    for membership in memberships:
        org = membership.organization
        if org.type == Organization.Type.BANK and membership.role in {
            UserMembership.Role.APPROVER,
            UserMembership.Role.RISK_EXPERT,
        }:
            return PERSONA_BANK_APPROVER, membership
    for membership in memberships:
        org = membership.organization
        if org.type in {
            Organization.Type.MANUFACTURER,
            Organization.Type.DISTRIBUTOR,
            Organization.Type.PHARMACY,
        } and membership.role in {
            UserMembership.Role.OWNER,
            UserMembership.Role.OPERATOR,
        }:
            return PERSONA_SUPPLIER, membership

    membership = memberships[0]
    if membership.organization.type == Organization.Type.BANK:
        if membership.role == UserMembership.Role.BANK_FINANCE:
            return PERSONA_BANK_FINANCE, membership
        return PERSONA_BANK_APPROVER, membership
    return PERSONA_SUPPLIER, membership


def _month_starts(count: int = 6) -> list[date]:
    today = timezone.localdate()
    year, month = today.year, today.month
    starts: list[date] = []
    for _ in range(count):
        starts.append(date(year, month, 1))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    starts.reverse()
    return starts


def _month_label(value: date) -> str:
    return f"{value.year}/{value.month:02d}"


def build_dashboard_for_user(user) -> dict:
    persona, membership = resolve_dashboard_persona(user)
    if persona is None or membership is None:
        return {
            "persona": None,
            "kpis": [],
            "charts": [],
            "table": {"title": "فعالیتی ثبت نشده", "columns": [], "rows": []},
        }

    requests = financing_requests_for_user(user)
    if persona == PERSONA_SUPPLIER:
        return _supplier_dashboard(user=user, membership=membership, requests=requests)
    if persona == PERSONA_BANK_APPROVER:
        return _approver_dashboard(user=user, membership=membership, requests=requests)
    return _finance_dashboard(user=user, membership=membership, requests=requests)


def _supplier_dashboard(*, user, membership, requests) -> dict:
    org = membership.organization
    org_requests = requests.filter(invoice__issuer_id=org.id)
    facilities = Facility.objects.filter(borrower_id=org.id)
    facility_limit = facilities.aggregate(total=Sum("limit"))["total"] or Decimal("0")
    facility_utilized = facilities.aggregate(total=Sum("utilized_amount"))["total"] or Decimal("0")
    available = facility_limit - facility_utilized

    pending_count = org_requests.filter(status=FinancingRequest.Status.REQUESTED).count()
    since = timezone.now() - timedelta(days=30)
    disbursed_30d = org_requests.filter(
        status=FinancingRequest.Status.DISBURSED, updated_at__gte=since
    ).aggregate(total=Sum("requested_amount"))["total"] or Decimal("0")

    status_rows = (
        org_requests.values("status")
        .annotate(count=Count("id"), amount=Sum("requested_amount"))
        .order_by("status")
    )
    status_map = {row["status"]: row for row in status_rows}

    month_starts = _month_starts(6)
    first_month = month_starts[0]
    monthly = {
        row["month"].date().replace(day=1) if hasattr(row["month"], "date") else row["month"]: row[
            "amount"
        ]
        or Decimal("0")
        for row in org_requests.filter(
            status=FinancingRequest.Status.DISBURSED, updated_at__gte=first_month
        )
        .annotate(month=TruncMonth("updated_at"))
        .values("month")
        .annotate(amount=Sum("requested_amount"))
    }

    recent = list(org_requests.order_by("-created_at", "-pk")[:8])
    return {
        "persona": PERSONA_SUPPLIER,
        "kpis": [
            _kpi("facility_limit", "سقف تسهیلات فعال", facility_limit),
            _kpi("facility_available", "مانده قابل استفاده", available),
            _kpi("pending_requests", "درخواست در انتظار", pending_count, unit="count"),
            _kpi("disbursed_30d", "پرداخت‌شده ۳۰ روز", disbursed_30d),
        ],
        "charts": [
            {
                "id": "disbursement_trend",
                "type": "line",
                "title": "روند پرداخت ماهانه",
                "series": [
                    {
                        "name": "پرداخت‌شده",
                        "points": [
                            {
                                "x": _month_label(start),
                                "y": float(monthly.get(start, Decimal("0"))),
                            }
                            for start in month_starts
                        ],
                    }
                ],
            },
            {
                "id": "requests_by_status",
                "type": "donut",
                "title": "توزیع وضعیت درخواست‌ها",
                "series": [
                    {
                        "name": "وضعیت",
                        "points": [
                            {
                                "x": STATUS_LABELS[status],
                                "y": float(status_map.get(status, {}).get("count") or 0),
                            }
                            for status in FinancingRequest.Status.values
                        ],
                    }
                ],
            },
        ],
        "table": {
            "title": "آخرین درخواست‌های تأمین مالی",
            "columns": [
                {"key": "title", "title": "عنوان"},
                {"key": "counterparty", "title": "خریدار"},
                {"key": "amount", "title": "مبلغ"},
                {"key": "created_at", "title": "تاریخ"},
                {"key": "status", "title": "وضعیت"},
            ],
            "rows": [_request_row(item) for item in recent],
        },
    }


def _approver_dashboard(*, user, membership, requests) -> dict:
    org = membership.organization
    bank_requests = requests.filter(
        models.Q(facility__lender_id=org.id) | models.Q(invoice__issuer__isnull=False)
    )
    # Prefer lender-scoped queue when facility is set; otherwise all visible bank-side requests
    queue = requests.filter(status=FinancingRequest.Status.REQUESTED).order_by("created_at", "pk")
    if Facility.objects.filter(lender_id=org.id).exists():
        queue = queue.filter(facility__lender_id=org.id)
        bank_requests = requests.filter(facility__lender_id=org.id)

    queue_amount = queue.aggregate(total=Sum("requested_amount"))["total"] or Decimal("0")
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)
    approved_today = bank_requests.filter(
        status=FinancingRequest.Status.APPROVED,
        updated_at__gte=today,
        updated_at__lt=tomorrow,
    ).count()
    rejected_today = bank_requests.filter(
        status=FinancingRequest.Status.REJECTED,
        updated_at__gte=today,
        updated_at__lt=tomorrow,
    ).count()

    since = today - timedelta(days=6)
    history_days = [since + timedelta(days=offset) for offset in range(7)]
    approved_by_day = {
        row["day"]: row["count"]
        for row in bank_requests.filter(
            status=FinancingRequest.Status.APPROVED,
            updated_at__date__gte=since,
        )
        .annotate(day=TruncDate("updated_at"))
        .values("day")
        .annotate(count=Count("id"))
    }
    rejected_by_day = {
        row["day"]: row["count"]
        for row in bank_requests.filter(
            status=FinancingRequest.Status.REJECTED,
            updated_at__date__gte=since,
        )
        .annotate(day=TruncDate("updated_at"))
        .values("day")
        .annotate(count=Count("id"))
    }

    queue_rows = list(queue.select_related("invoice__issuer", "invoice__buyer")[:10])
    return {
        "persona": PERSONA_BANK_APPROVER,
        "kpis": [
            _kpi("queue_count", "صف تأیید", queue.count(), unit="count"),
            _kpi("queue_amount", "مبلغ در صف", queue_amount),
            _kpi("approved_today", "تأیید امروز", approved_today, unit="count"),
            _kpi("rejected_today", "رد امروز", rejected_today, unit="count"),
        ],
        "charts": [
            {
                "id": "approve_reject_7d",
                "type": "bar",
                "title": "تأیید و رد ۷ روز اخیر",
                "series": [
                    {
                        "name": "تأیید",
                        "points": [
                            {"x": day.isoformat(), "y": float(approved_by_day.get(day, 0))}
                            for day in history_days
                        ],
                    },
                    {
                        "name": "رد",
                        "points": [
                            {"x": day.isoformat(), "y": float(rejected_by_day.get(day, 0))}
                            for day in history_days
                        ],
                    },
                ],
            },
            {
                "id": "queue_by_amount",
                "type": "donut",
                "title": "ترکیب مبلغ صف تأیید",
                "series": [
                    {
                        "name": "صف",
                        "points": [
                            {
                                "x": item.invoice.issuer.name if item.invoice_id else "—",
                                "y": float(item.requested_amount),
                            }
                            for item in queue_rows
                        ]
                        or [{"x": "خالی", "y": 0.0}],
                    }
                ],
            },
        ],
        "table": {
            "title": "صف تأیید درخواست‌ها",
            "columns": [
                {"key": "title", "title": "عنوان"},
                {"key": "counterparty", "title": "متقاضی"},
                {"key": "amount", "title": "مبلغ"},
                {"key": "created_at", "title": "تاریخ"},
                {"key": "status", "title": "وضعیت"},
            ],
            "rows": [_request_row(item, counterparty="issuer") for item in queue_rows],
        },
    }


def _finance_dashboard(*, user, membership, requests) -> dict:
    org = membership.organization
    bank_requests = requests.filter(facility__lender_id=org.id)
    if not bank_requests.exists():
        bank_requests = requests

    approved_qs = bank_requests.filter(status=FinancingRequest.Status.APPROVED).order_by(
        "updated_at", "pk"
    )
    approved_amount = approved_qs.aggregate(total=Sum("requested_amount"))["total"] or Decimal("0")
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)
    disbursed_today = bank_requests.filter(
        status=FinancingRequest.Status.DISBURSED,
        updated_at__gte=today,
        updated_at__lt=tomorrow,
    ).aggregate(total=Sum("requested_amount"))["total"] or Decimal("0")

    facilities = list(Facility.objects.filter(lender_id=org.id).select_related("borrower"))
    limit_total = sum((f.limit for f in facilities), Decimal("0"))
    utilized_total = sum((f.utilized_amount for f in facilities), Decimal("0"))
    utilization_pct = (
        (utilized_total / limit_total * Decimal("100")) if limit_total else Decimal("0")
    )

    month_starts = _month_starts(6)
    first_month = month_starts[0]
    monthly = {
        (
            row["month"].date().replace(day=1)
            if hasattr(row["month"], "date")
            else row["month"]
        ): row["amount"]
        or Decimal("0")
        for row in bank_requests.filter(
            status=FinancingRequest.Status.DISBURSED, updated_at__gte=first_month
        )
        .annotate(month=TruncMonth("updated_at"))
        .values("month")
        .annotate(amount=Sum("requested_amount"))
    }

    return {
        "persona": PERSONA_BANK_FINANCE,
        "kpis": [
            _kpi("ready_count", "آماده پرداخت", approved_qs.count(), unit="count"),
            _kpi("ready_amount", "مبلغ صف پرداخت", approved_amount),
            _kpi("disbursed_today", "پرداخت‌شده امروز", disbursed_today),
            _kpi("utilization", "Utilization تسهیلات", f"{utilization_pct.quantize(Decimal('0.01'))}", unit="percent"),
        ],
        "charts": [
            {
                "id": "disbursement_trend",
                "type": "line",
                "title": "روند پرداخت ماهانه",
                "series": [
                    {
                        "name": "پرداخت‌شده",
                        "points": [
                            {
                                "x": _month_label(start),
                                "y": float(monthly.get(start, Decimal("0"))),
                            }
                            for start in month_starts
                        ],
                    }
                ],
            },
            {
                "id": "facility_utilization",
                "type": "bar",
                "title": "Utilization تسهیلات",
                "series": [
                    {
                        "name": "سقف",
                        "points": [
                            {
                                "x": facility.borrower.name,
                                "y": float(facility.limit),
                            }
                            for facility in facilities
                        ]
                        or [{"x": "بدون تسهیلات", "y": 0.0}],
                    },
                    {
                        "name": "مصرف‌شده",
                        "points": [
                            {
                                "x": facility.borrower.name,
                                "y": float(facility.utilized_amount),
                            }
                            for facility in facilities
                        ]
                        or [{"x": "بدون تسهیلات", "y": 0.0}],
                    },
                ],
            },
        ],
        "table": {
            "title": "درخواست‌های آماده پرداخت",
            "columns": [
                {"key": "title", "title": "عنوان"},
                {"key": "counterparty", "title": "متقاضی"},
                {"key": "amount", "title": "مبلغ"},
                {"key": "created_at", "title": "تاریخ"},
                {"key": "status", "title": "وضعیت"},
            ],
            "rows": [
                _request_row(item, counterparty="issuer")
                for item in approved_qs.select_related("invoice__issuer", "invoice__buyer")[:10]
            ],
        },
    }


def _request_row(item: FinancingRequest, *, counterparty: str = "buyer") -> dict:
    if counterparty == "issuer":
        party = item.invoice.issuer.name if item.invoice_id else "—"
    else:
        party = item.invoice.buyer.name if item.invoice_id and item.invoice.buyer_id else "—"
    invoice_number = item.invoice.number if item.invoice_id else item.pk
    return {
        "id": str(item.pk),
        "title": f"درخواست {invoice_number}",
        "counterparty": party,
        "amount": _dec(item.requested_amount),
        "created_at": timezone.localtime(item.created_at).strftime("%Y-%m-%d"),
        "status": item.status,
        "status_label": STATUS_LABELS.get(item.status, item.status),
    }
