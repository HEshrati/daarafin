import hashlib
import json

from django.conf import settings
from django.db import models

from common.errors import DomainError


class IdempotencyRecord(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)
    operation = models.CharField(max_length=100, default="")
    key = models.CharField(max_length=255)
    request_hash = models.CharField(max_length=64, default="")
    response_payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("actor", "operation", "key"), name="unique_idempotency_request"
            )
        ]


def _payload_hash(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def begin_idempotent_request(*, actor, operation: str, key: str | None, payload):
    if not key or not key.strip():
        raise DomainError("idempotency_key_required", "هدر Idempotency-Key الزامی است.")
    if len(key) > 255:
        raise DomainError("idempotency_key_too_long", "طول Idempotency-Key بیش از حد مجاز است.")

    request_hash = _payload_hash(payload)
    record, created = IdempotencyRecord.objects.get_or_create(
        actor=actor,
        operation=operation,
        key=key,
        defaults={"request_hash": request_hash},
    )
    if not created and record.request_hash != request_hash:
        raise DomainError(
            "idempotency_key_reused",
            "این Idempotency-Key قبلاً برای درخواست دیگری استفاده شده است.",
            status_code=409,
        )
    if not created and not record.response_payload:
        raise DomainError(
            "idempotency_request_in_progress",
            "درخواستی با این Idempotency-Key در حال پردازش است.",
            status_code=409,
        )
    return record, not created


def complete_idempotent_request(record, response_payload: dict) -> dict:
    record.response_payload = response_payload
    record.save(update_fields=("response_payload",))
    return response_payload
