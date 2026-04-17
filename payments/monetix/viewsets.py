from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authentication.models import CustomUser
from . import serializers
from .models import WalletHistory, UserAccount, UserWallet, UserBinanceAccount
from .serializers import WalletHistorySerializer


class UserWalletViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only wallet access. Users can only see their own wallet.
    Admins (is_staff) can retrieve any wallet by user id via /balance/{user_id}/.
    """
    serializer_class = serializers.UserWalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserWallet.objects.filter(user=self.request.user)

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Return wallet for the given user id (own wallet only unless staff)."""
        if not request.user.is_staff and str(request.user.id) != str(pk):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        user_wallet = get_object_or_404(UserWallet, user_id=pk)
        return Response(serializers.UserWalletSerializer(user_wallet).data)


class WalletHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only wallet history. Users see only their own transactions.
    """
    serializer_class = WalletHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WalletHistory.objects.filter(user_wallet__user=self.request.user)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Return transaction history for the given user id (own only unless staff)."""
        if not request.user.is_staff and str(request.user.id) != str(pk):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            user_wallet = UserWallet.objects.get(user_id=pk)
            return Response(WalletHistorySerializer(user_wallet.wallet_history.all(), many=True).data)
        except UserWallet.DoesNotExist:
            return Response({'error': 'Wallet not found.'}, status=status.HTTP_404_NOT_FOUND)


class UserAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """Payment card accounts — read-only, own records only."""
    serializer_class = serializers.UserAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserAccount.objects.filter(userwallet__user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        try:
            user_account = UserAccount.objects.get(user_wallet__user_id=kwargs['pk'])
            if not request.user.is_staff and user_account.user_wallet.user != request.user:
                return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            return Response(self.get_serializer(user_account).data)
        except UserAccount.DoesNotExist:
            return Response({'error': 'User account not found.'}, status=status.HTTP_404_NOT_FOUND)


class UserBinanceAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """Binance accounts — read-only, own records only."""
    serializer_class = serializers.UserBinanceAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserBinanceAccount.objects.filter(user_wallet__user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        try:
            binance_account = UserBinanceAccount.objects.get(user_wallet__user_id=kwargs['pk'])
            if not request.user.is_staff and binance_account.user_wallet.user != request.user:
                return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            return Response({'user_id': kwargs['pk'], 'binance_id': binance_account.number})
        except UserBinanceAccount.DoesNotExist:
            return Response({'error': 'Binance account not found.'}, status=status.HTTP_404_NOT_FOUND)
