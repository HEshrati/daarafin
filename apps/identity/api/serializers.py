from rest_framework import serializers

from apps.identity.models import User


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "mobile", "is_mfa_enabled")


class SessionSerializer(serializers.Serializer):
    current = serializers.BooleanField()
    authenticated_at = serializers.DateTimeField()
