import uuid

import boto3
from django.conf import settings

from common.errors import DomainError

from .models import Document

ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png"}
MAX_SIZE = 10 * 1024 * 1024


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def presign_upload(*, case, user, filename, mime, size, document_type):
    if mime not in ALLOWED_MIME:
        raise DomainError("invalid_mime", "نوع فایل مجاز نیست.")
    if size > MAX_SIZE:
        raise DomainError("file_too_large", "حجم فایل بیشتر از ۱۰ مگابایت است.")
    key = f"onboarding/{case.pk}/{uuid.uuid4().hex}-{filename.rsplit('.', 1)[-1]}"
    version = Document.objects.filter(onboarding_case=case, document_type=document_type).count() + 1
    doc = Document.objects.create(
        onboarding_case=case,
        document_type=document_type,
        storage_key=key,
        version=version,
        uploaded_by=user,
    )
    url = s3_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": key, "ContentType": mime},
        ExpiresIn=300,
    )
    return doc, url


def complete_upload(*, document, checksum):
    if len(checksum) != 64:
        raise DomainError("invalid_checksum", "checksum نامعتبر است.")
    document.checksum_sha256 = checksum
    document.save(update_fields=("checksum_sha256",))
    return document
