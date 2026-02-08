from rest_framework import permissions
from rest_framework import viewsets

from . import serializers
from .models import AccountingHistory, Accounting


class AccountingViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.AccountingSerializer
    permission_classes = (permissions.AllowAny,)
    queryset = Accounting.objects.all()


class AccountingHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.AccountingHistorySerializer
    permission_classes = (permissions.AllowAny,)
    queryset = AccountingHistory.objects.all()
