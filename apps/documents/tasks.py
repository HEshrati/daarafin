from celery import shared_task

from .models import Document


@shared_task(queue="documents")
def scan_document(document_id):
    updated = (
        Document.objects.filter(pk=document_id)
        .exclude(checksum_sha256="")
        .update(scan_status=Document.ScanStatus.CLEAN)
    )
    return "clean" if updated else "skipped"
