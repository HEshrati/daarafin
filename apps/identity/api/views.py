from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeSerializer, SessionSerializer


class MeView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = MeSerializer

    def get(self, request):
        return Response(MeSerializer(request.user).data)


class SessionsView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SessionSerializer

    def get(self, request):
        data = [{"current": True, "authenticated_at": request.user.last_login or timezone.now()}]
        return Response(SessionSerializer(data, many=True).data)
