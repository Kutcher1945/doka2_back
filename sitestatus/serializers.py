from rest_framework import serializers
from .models import SiteStatus


class SiteStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteStatus
        fields = ('is_enabled',)
