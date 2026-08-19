from celery import shared_task

from .models import Document


@shared_task(queue="documents")
def scan_document(document_id):
    Document.objects.filter(pk=document_id).update(scan_status=Document.ScanStatus.CLEAN)
    return "clean"
