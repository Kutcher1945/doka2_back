from django.urls import path
from .viewsets import SiteStatusView

urlpatterns = [
    path('', SiteStatusView.as_view(), name='site-status'),
]
