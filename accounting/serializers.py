from rest_framework.serializers import ModelSerializer
from .models import *


class AccountingSerializer(ModelSerializer):
    class Meta:
        model = Accounting
        fields = ('id', 'balance')


class AccountingHistorySerializer(ModelSerializer):
    class Meta:
        model = AccountingHistory
        fields = ('id', 'balance', 'bonus_balance', 'blocked_balance', 'currency', 'payout_commission')

