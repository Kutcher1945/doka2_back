from rest_framework.serializers import ModelSerializer
from .models import Accounting, AccountingHistory


class AccountingSerializer(ModelSerializer):
    class Meta:
        model = Accounting
        fields = ('id', 'balance')


class AccountingHistorySerializer(ModelSerializer):
    class Meta:
        model = AccountingHistory
        fields = ('id', 'accounting', 'lobby', 'datetime', 'service_earning', 'user')
