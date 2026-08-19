from rest_framework import serializers


class PresignSerializer(serializers.Serializer):
    case_id = serializers.IntegerField()
    filename = serializers.CharField(max_length=255)
    mime = serializers.CharField(max_length=100)
    size = serializers.IntegerField(min_value=1)
    document_type = serializers.CharField(max_length=50)


class CompleteSerializer(serializers.Serializer):
    checksum_sha256 = serializers.RegexField(r"^[0-9A-Fa-f]{64}$")


class UrlSerializer(serializers.Serializer):
    download_url = serializers.URLField()
    expires_in = serializers.IntegerField()
