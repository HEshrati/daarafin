import hashlib
import re
import uuid

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.db import transaction
from django.db.models import Max

from apps.audit.services import record_event
from apps.onboarding.models import OnboardingCase
from common.errors import DomainError

from .models import Document

ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png"}
MIME_EXTENSIONS = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}
MAX_SIZE = 10 * 1024 * 1024


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


@transaction.atomic
def presign_upload(*, case, user, filename, mime, size, document_type):
    if mime not in ALLOWED_MIME:
        raise DomainError("invalid_mime", "نوع فایل مجاز نیست.")
    if size <= 0 or size > MAX_SIZE:
        raise DomainError("invalid_file_size", "حجم فایل باید بین ۱ بایت و ۱۰ مگابایت باشد.")

    locked_case = OnboardingCase.objects.select_for_update().get(pk=case.pk)
    if locked_case.status not in {
        OnboardingCase.Status.DRAFT,
        OnboardingCase.Status.NEED_CHANGES,
    }:
        raise DomainError("case_not_editable", "در وضعیت فعلی امکان بارگذاری مدرک وجود ندارد.")

    extension = MIME_EXTENSIONS[mime]
    key = f"onboarding/{locked_case.pk}/{uuid.uuid4().hex}.{extension}"
    latest_version = (
        Document.objects.filter(onboarding_case=locked_case, document_type=document_type).aggregate(
            latest=Max("version")
        )["latest"]
        or 0
    )
    document = Document.objects.create(
        onboarding_case=locked_case,
        document_type=document_type,
        storage_key=key,
        version=latest_version + 1,
        uploaded_by=user,
    )
    url = s3_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": key, "ContentType": mime},
        ExpiresIn=300,
    )
    record_event(
        actor=user,
        action="document.presign",
        obj=document,
        before={},
        after={"document_type": document.document_type, "version": document.version},
    )
    return document, url


def complete_upload(*, document, checksum, actor=None, correlation_id=""):
    checksum = checksum.lower()
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise DomainError("invalid_checksum", "checksum نامعتبر است.")

    with transaction.atomic():
        locked = Document.objects.select_for_update().get(pk=document.pk)
        if locked.checksum_sha256:
            if locked.checksum_sha256 != checksum:
                raise DomainError(
                    "upload_already_completed",
                    "این بارگذاری قبلاً با checksum دیگری تکمیل شده است.",
                    status_code=409,
                )
            return locked
        storage_key = locked.storage_key

    digest = hashlib.sha256()
    total_size = 0
    try:
        response = s3_client().get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=storage_key)
        body = response["Body"]
        try:
            for chunk in body.iter_chunks(chunk_size=64 * 1024):
                total_size += len(chunk)
                if total_size > MAX_SIZE:
                    raise DomainError("file_too_large", "حجم فایل بیشتر از ۱۰ مگابایت است.")
                digest.update(chunk)
        finally:
            body.close()
    except ClientError as exc:
        raise DomainError(
            "upload_not_found",
            "فایل بارگذاری‌شده در فضای ذخیره‌سازی پیدا نشد.",
            status_code=409,
        ) from exc

    if total_size == 0 or digest.hexdigest() != checksum:
        raise DomainError("checksum_mismatch", "checksum فایل بارگذاری‌شده مطابقت ندارد.")

    with transaction.atomic():
        locked = Document.objects.select_for_update().get(pk=document.pk)
        if locked.checksum_sha256 and locked.checksum_sha256 != checksum:
            raise DomainError(
                "upload_already_completed",
                "این بارگذاری قبلاً با checksum دیگری تکمیل شده است.",
                status_code=409,
            )
        locked.checksum_sha256 = checksum
        locked.save(update_fields=("checksum_sha256",))
        record_event(
            actor=actor,
            action="document.complete",
            obj=locked,
            before={"checksum_sha256": ""},
            after={"checksum_sha256": checksum},
            correlation_id=correlation_id,
        )
        return locked
