from rest_framework import serializers


class PresignSerializer(serializers.Serializer):
    case_id = serializers.IntegerField()
    filename = serializers.CharField()
    mime = serializers.CharField()
    size = serializers.IntegerField()
    document_type = serializers.CharField()


class CompleteSerializer(serializers.Serializer):
    checksum_sha256 = serializers.CharField()


class UrlSerializer(serializers.Serializer):
    download_url = serializers.URLField()
    expires_in = serializers.IntegerField()
