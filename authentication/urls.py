from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import *
from .viewsets import *

router = DefaultRouter()
router.register('', CustomUserModelViewSet)

urlpatterns = [
    path('data/', UserRetrieveUpdateDestroyAPIView.as_view(),
         name='user-data'),
    path('users/', include(router.urls)),
    path('check_user/', check_user),
    path('send_sms/', sms_send),
    path('verify_sms_code/', verify_sms_code),
    path('restore_password/', restore_password),
    path('restore_password/submit/', restore_password_submit),
    path('change_password/', change_password),
    path('online_statuses/', UserOnlineStatusesView.as_view()),
    path('set_status/', UserSetStatusView.as_view()),
    path('my_id/', get_my_id),
    path('verification/', include('authentication.verification.urls')),
]
