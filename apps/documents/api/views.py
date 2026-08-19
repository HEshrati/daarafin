from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents import services
from apps.documents.models import Document
from apps.documents.tasks import scan_document
from apps.onboarding.selectors import cases_for_user

from .serializers import CompleteSerializer, PresignSerializer, UrlSerializer


class PresignView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PresignSerializer

    def post(self, request):
        s = PresignSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        case = generics.get_object_or_404(cases_for_user(request.user), pk=v.pop("case_id"))
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
        services.complete_upload(document=doc, checksum=s.validated_data["checksum_sha256"])
        scan_document.delay(doc.pk)
        return Response({"status": "pending"})


class DownloadUrlView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UrlSerializer

    def get(self, request, pk):
        doc = generics.get_object_or_404(
            Document, pk=pk, onboarding_case__in=cases_for_user(request.user)
        )
        url = services.s3_client().generate_presigned_url(
            "get_object",
            Params={
                "Bucket": __import__("django.conf").conf.settings.AWS_STORAGE_BUCKET_NAME,
                "Key": doc.storage_key,
            },
            ExpiresIn=60,
        )
        return Response({"download_url": url, "expires_in": 60})
