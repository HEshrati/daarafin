import hashlib
import json

from .models import AuditEvent


def payload_hash(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def record_event(*, actor, action, obj, before, after, correlation_id=""):
    return AuditEvent.objects.create(
        actor=actor,
        action=action,
        object_type=obj._meta.label_lower,
        object_id=str(obj.pk),
        before_hash=payload_hash(before),
        after_hash=payload_hash(after),
        correlation_id=correlation_id,
    )
