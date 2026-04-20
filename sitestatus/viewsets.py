from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import SiteStatus
from .serializers import SiteStatusSerializer


class SiteStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        site_status = SiteStatus.objects.first()
        if site_status is None:
            return Response({'maintenance': False, 'message': ''})
        return Response(SiteStatusSerializer(site_status).data)
