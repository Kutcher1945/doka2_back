from rest_framework import generics, permissions, status, views, viewsets
from rest_framework.response import Response

from authentication import UserOnlineStatuses
from payments.monetix.models import UserWallet
from .serializers import CustomUserSerializer, CustomUserRetrieveSerializer
from .models import CustomUser
from .verification.models import UserVerification


class CustomUserModelViewSet(viewsets.ModelViewSet):
    """
    User CRUD ViewSet.

    - create  (POST)  — public, no auth required (registration)
    - all other actions — require authentication
    """
    serializer_class = CustomUserSerializer
    queryset = CustomUser.objects.all()

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.set_password(instance.password)

        # UserWallet.user is a FK to CustomUser — no need to store it back on the user.
        UserWallet.objects.create(user=instance)
        user_verification = UserVerification.objects.create(user=instance)

        instance.verification = user_verification
        instance.save()


class UserRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserRetrieveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserOnlineStatusesView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        choices = UserOnlineStatuses.choices
        return Response([{'name': name, 'code': code} for code, name in choices])


class UserSetStatusView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        status_value = request.data.get('status', 'ONLINE')
        if status_value not in UserOnlineStatuses.values:
            return Response({'error': 'Status not found.'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.online_status = status_value
        request.user.save()
        return Response(status=status.HTTP_200_OK)
