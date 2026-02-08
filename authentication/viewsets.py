from rest_framework import generics, permissions
from rest_framework import viewsets, views
from rest_framework.response import Response

from authentication import UserOnlineStatuses
from payments.monetix.models import UserWallet
from .serializers import *
from .verification.models import UserVerification


class CustomUserModelViewSet(viewsets.ModelViewSet):
    serializer_class = CustomUserSerializer
    permission_classes = (permissions.AllowAny,)
    queryset = CustomUser.objects.all()

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.set_password(instance.password)
        # send_otp.send_verification_sms(instance.cleaned_data.get('phone_number'))
        user_wallet = UserWallet.objects.create(
            user=instance
        )
        user_verification = UserVerification.objects.create(
            user=instance
        )

        instance.user_wallet = user_wallet
        instance.verification = user_verification

        instance.save()


class UserRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserRetrieveSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None


class UserOnlineStatusesView(views.APIView):

    def get(self, request, *args, **kwargs):
        choices = UserOnlineStatuses.choices
        result = [{'name': name, 'code': code} for code, name in choices]
        return Response(result)


class UserSetStatusView(views.APIView):

    def post(self, request, *args, **kwargs):
        user = request.user
        status = request.data.get('status', 'ONLINE')
        if status not in UserOnlineStatuses.values:
            return Response(status=400, data={"error": "Status not found!"})
        user.online_status = status
        user.save()
        return Response(status=200)
