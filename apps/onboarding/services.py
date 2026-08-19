from django.db import IntegrityError, transaction

from apps.audit.services import record_event
from apps.organizations.models import Organization, UserMembership
from apps.organizations.services import DEFAULT_ROLE_SCOPES
from common.errors import DomainError
from common.idempotency import begin_idempotent_request, complete_idempotent_request
from common.permissions import ensure_maker_checker, has_active_scope

from .models import OnboardingCase

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
    locked = OnboardingCase.objects.select_for_update().get(pk=case.pk)
    if target not in ALLOWED[locked.status]:
        raise DomainError("invalid_transition", "تغییر وضعیت درخواست‌شده مجاز نیست.")
    if target in {"approved", "rejected", "need_changes"}:
        ensure_maker_checker(actor=actor, maker=locked.requested_by)
    if target in {"rejected", "need_changes"} and not reason:
        raise DomainError("reason_required", "ثبت دلیل الزامی است.")
    before = {"status": locked.status, "reason": locked.reason}
    locked.status = target
    locked.reason = reason
    if target in {"approved", "rejected", "need_changes"}:
        locked.reviewed_by = actor
    locked.save(update_fields=("status", "reason", "reviewed_by", "updated_at"))
    record_event(
        actor=actor,
        action=f"onboarding.{target}",
        obj=locked,
        before=before,
        after={"status": locked.status, "reason": locked.reason},
        correlation_id=correlation_id,
    )
    return locked


@transaction.atomic
def submit_case(*, case, actor, idempotency_key, correlation_id=""):
    record, replay = begin_idempotent_request(
        actor=actor,
        operation="onboarding.submit",
        key=idempotency_key,
        payload={"case_id": case.pk},
    )
    if replay:
        return OnboardingCase.objects.get(pk=record.response_payload["case_id"])

    required = {"registration", "articles"}
    clean = set(case.documents.filter(scan_status="clean").values_list("document_type", flat=True))
    missing = required - clean
    if missing:
        raise DomainError("documents_incomplete", f"مدارک کامل نیست: {', '.join(sorted(missing))}")
    submitted = transition_case(
        case=case, target="submitted", actor=actor, correlation_id=correlation_id
    )
    complete_idempotent_request(record, {"case_id": submitted.pk, "status": submitted.status})
    return submitted


@transaction.atomic
def create_case(*, actor, name, national_id, organization_type, correlation_id=""):
    organization, created = Organization.objects.get_or_create(
        national_id=national_id,
        defaults={"name": name, "type": organization_type},
    )
    if created:
        UserMembership.objects.create(
            user=actor,
            organization=organization,
            role=UserMembership.Role.OWNER,
            scopes=DEFAULT_ROLE_SCOPES["owner"].copy(),
        )
    elif not has_active_scope(
        user=actor, organization_id=organization.pk, scope="manage_onboarding"
    ):
        raise DomainError(
            "organization_access_denied",
            "سازمانی با این شناسه ملی قبلاً ثبت شده است.",
            status_code=403,
        )

    try:
        with transaction.atomic():
            case = OnboardingCase.objects.create(organization=organization, requested_by=actor)
    except IntegrityError as exc:
        raise DomainError(
            "active_onboarding_exists",
            "برای این سازمان یک پرونده فعال وجود دارد.",
            status_code=409,
        ) from exc
    record_event(
        actor=actor,
        action="onboarding.create",
        obj=case,
        before={},
        after={"status": case.status, "organization_id": organization.pk},
        correlation_id=correlation_id,
    )
    return case
