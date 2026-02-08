from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import *
from .viewsets import *

router = DefaultRouter()
router.register(r'user_wallet', UserWalletViewSet, basename='user_wallet')
router.register(r'wallet_history', WalletHistoryViewSet, basename='wallet_history')
router.register(r'user_account', UserAccountViewSet, basename='user_account')
router.register(r'user_binance_account', UserBinanceAccountViewSet, basename='user_binance_account')


urlpatterns = [
    path('', include(router.urls)),
    path('payments_handler/', payments_handler),
    path('callback/replenish', replenish_callback),
    path('callback/withdrawal', withdrawal_callback),
]
