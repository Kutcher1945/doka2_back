from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import *
from .viewsets import *

router = DefaultRouter()
router.register(r'accounting', AccountingViewSet, basename='accounting')
router.register(r'accounting_history', AccountingHistoryViewSet, basename='accounting_history')


urlpatterns = [
    path('', include(router.urls)),
]
