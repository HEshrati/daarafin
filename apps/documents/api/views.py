from django.conf import settings
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents import services
from apps.documents.models import Document
from apps.documents.tasks import scan_document
from apps.onboarding.selectors import cases_for_user
from common.permissions import ensure_active_scope

from .serializers import CompleteSerializer, PresignSerializer, UrlSerializer


class PresignView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PresignSerializer

    def post(self, request):
        s = PresignSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        case = generics.get_object_or_404(cases_for_user(request.user), pk=v.pop("case_id"))
        ensure_active_scope(
            user=request.user,
            organization_id=case.organization_id,
            scope="manage_onboarding",
        )
        doc, url = services.presign_upload(case=case, user=request.user, **v)
        return Response({"document_id": doc.pk, "upload_url": url, "expires_in": 300})


class CompleteView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CompleteSerializer

    def post(self, request, pk):
        doc = generics.get_object_or_404(
            Document, pk=pk, onboarding_case__in=cases_for_user(request.user)
        )
        s = CompleteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ensure_active_scope(
            user=request.user,
            organization_id=doc.onboarding_case.organization_id,
            scope="manage_onboarding",
        )
        doc = services.complete_upload(
            document=doc,
            checksum=s.validated_data["checksum_sha256"],
            actor=request.user,
            correlation_id=getattr(request, "correlation_id", ""),
        )
        scan_document.delay(doc.pk)
        return Response({"status": "pending"})


class DownloadUrlView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UrlSerializer

    def get(self, request, pk):
        doc = generics.get_object_or_404(
            Document,
            pk=pk,
            scan_status=Document.ScanStatus.CLEAN,
            onboarding_case__in=cases_for_user(request.user),
        )
        url = services.s3_client().generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": doc.storage_key,
            },
            ExpiresIn=60,
        )
        return Response({"download_url": url, "expires_in": 60})
