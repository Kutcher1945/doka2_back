from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()


urlpatterns = [
    path('', include(router.urls)),
    path('result/', post_report_result),
    path('report_new_player/', report_new_player),
]
