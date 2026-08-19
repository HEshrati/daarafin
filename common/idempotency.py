from django.db import models


class IdempotencyRecord(models.Model):
    key = models.CharField(max_length=255, unique=True)
    response_payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
