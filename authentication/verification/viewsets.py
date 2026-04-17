from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from . import serializers
from .models import UserVerification, VerificationHistory


class UserVerificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.UserVerificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserVerification.objects.filter(user=self.request.user)


class VerificationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.VerificationHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return VerificationHistory.objects.filter(
            user_verification__user=self.request.user
        )
