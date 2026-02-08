from rest_framework.serializers import ModelSerializer
from .models import *


class UserWalletSerializer(ModelSerializer):
    class Meta:
        model = UserWallet
        fields = ('id', 'balance', 'bonus_balance', 'blocked_balance', 'currency', 'payout_commission')


class WalletHistorySerializer(ModelSerializer):

    class Meta:
        model = WalletHistory
        fields = ('pay_time', 'status', 'amount', 'currency', 'payment_id', 'method', 'type', 'payout_commission')


class UserAccountSerializer(ModelSerializer):

    class Meta:
        model = UserAccount
        fields = ('number', 'type', 'card_holder', 'expiry_month', 'expiry_year')


class UserBinanceAccountSerializer(ModelSerializer):
    class Meta:
        model = UserBinanceAccount
        fields = ('number',)

