from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import *
from .viewsets import *

router = DefaultRouter()
router.register(r'user_verification', UserVerificationViewSet, basename='user_verification')
router.register(r'verification_history', VerificationHistoryViewSet, basename='verification_history')

urlpatterns = [
    path('generate_verification_url/', generate_verification_url),
    path('get_verification_data/', get_verification_data),
    path('verification_callback/', verification_callback),
]
