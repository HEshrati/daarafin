from django.db import transaction

from apps.audit.services import record_event
from common.errors import DomainError
from common.permissions import ensure_maker_checker

ALLOWED = {
    "draft": {"submitted", "suspended"},
    "submitted": {"under_review", "suspended"},
    "under_review": {"approved", "rejected", "need_changes", "suspended"},
    "need_changes": {"submitted", "suspended"},
    "approved": {"suspended"},
    "rejected": set(),
    "suspended": set(),
}


@transaction.atomic
def transition_case(*, case, target, actor, reason="", correlation_id=""):
    if target not in ALLOWED[case.status]:
        raise DomainError("invalid_transition", "تغییر وضعیت درخواست‌شده مجاز نیست.")
    if target in {"approved", "rejected", "need_changes"}:
        ensure_maker_checker(actor=actor, maker=case.requested_by)
    if target in {"rejected", "need_changes"} and not reason:
        raise DomainError("reason_required", "ثبت دلیل الزامی است.")
    before = {"status": case.status, "reason": case.reason}
    case.status = target
    case.reason = reason
    if target in {"approved", "rejected", "need_changes"}:
        case.reviewed_by = actor
    case.save(update_fields=("status", "reason", "reviewed_by", "updated_at"))
    record_event(
        actor=actor,
        action=f"onboarding.{target}",
        obj=case,
        before=before,
        after={"status": case.status, "reason": case.reason},
        correlation_id=correlation_id,
    )
    return case


def submit_case(*, case, actor, idempotency_key, correlation_id=""):
    if not idempotency_key:
        raise DomainError("idempotency_key_required", "هدر Idempotency-Key الزامی است.")
    required = {"registration", "articles"}
    clean = set(case.documents.filter(scan_status="clean").values_list("document_type", flat=True))
    missing = required - clean
    if missing:
        raise DomainError("documents_incomplete", f"مدارک کامل نیست: {', '.join(sorted(missing))}")
    return transition_case(
        case=case, target="submitted", actor=actor, correlation_id=correlation_id
    )
