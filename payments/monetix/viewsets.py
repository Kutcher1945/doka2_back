from authentication.models import *
from authentication.models import CustomUser
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from . import serializers
from .models import WalletHistory, UserAccount, UserWallet, UserBinanceAccount
from .serializers import WalletHistorySerializer


class UserWalletViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserWalletSerializer
    permission_classes = (permissions.AllowAny,)
    queryset = None

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        current_user = get_object_or_404(CustomUser, id=pk)
        user_wallet = get_object_or_404(UserWallet, user=current_user)
        serializer = serializers.UserWalletSerializer(user_wallet)
        return Response(serializer.data)


class WalletHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.WalletHistorySerializer
    permission_classes = (permissions.AllowAny,)
    queryset = WalletHistory.objects.all()

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        try:
            current_user = CustomUser.objects.get(id=pk)
            user_wallet = UserWallet.objects.get(user=current_user)
            serializer = WalletHistorySerializer(user_wallet.wallet_history.all(), many=True)
            return Response(serializer.data)
        except (CustomUser.DoesNotExist, UserWallet.DoesNotExist):
            return Response({'error': 'User or user wallet not found.'}, status=status.HTTP_404_NOT_FOUND)


class UserAccountViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserAccountSerializer
    permission_classes = (permissions.AllowAny,)
    queryset = UserAccount.objects.all()

    def retrieve(self, request, *args, **kwargs):
        try:
            user_account = UserAccount.objects.get(user_wallet__user_id=kwargs['pk'])
            serializer = self.get_serializer(user_account)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserAccount.DoesNotExist:
            error_message = 'User account not found.'
            return Response({'error': error_message}, status=status.HTTP_404_NOT_FOUND)


class UserBinanceAccountViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UserBinanceAccountSerializer
    permission_classes = (permissions.AllowAny,)
    queryset = UserBinanceAccount.objects.all()

    def retrieve(self, request, *args, **kwargs):
        try:
            binance_account = UserBinanceAccount.objects.get(user_wallet__user_id=kwargs['pk'])
            binance_id = binance_account.number

            response_data = {
                'user_id': kwargs['pk'],
                'binance_id': binance_id
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except UserBinanceAccount.DoesNotExist:
            error_message = 'Binance ID not created for the user.'
            return Response({'error': error_message}, status=status.HTTP_404_NOT_FOUND)
