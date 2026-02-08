from django.http import Http404
from rest_framework import permissions, viewsets

from . import serializers
from .models import *


class UserVerificationViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserVerificationSerializer
    permission_classes = (permissions.AllowAny,)
    queryset = None

    def get_queryset(self):
        """
        Get user_verification by id_user
        """

        id_user = self.request.GET.get('id_user')
        if not id_user:
            raise Http404('id_user parameter is missing.')

        queryset = UserVerification.objects.filter(user_id=id_user)
        return queryset


class VerificationHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.VerificationHistorySerializer
    permission_classes = (permissions.AllowAny,)
    queryset = VerificationHistory.objects.all()
