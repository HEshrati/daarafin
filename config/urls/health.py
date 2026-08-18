import boto3
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.urls import path


def health(request):
    checks = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"
    try:
        cache.set("health", "ok", 5)
        checks["redis"] = "ok" if cache.get("health") == "ok" else "error"
    except Exception:
        checks["redis"] = "error"
    try:
        boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        ).head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
        checks["minio"] = "ok"
    except Exception:
        checks["minio"] = "error"
    healthy = all(value == "ok" for value in checks.values())
    return JsonResponse(
        {"status": "ok" if healthy else "degraded", "checks": checks},
        status=200 if healthy else 503,
    )


urlpatterns = [path("", health, name="health")]
