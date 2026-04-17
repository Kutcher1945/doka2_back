from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from payments.monetix.models import UserWallet


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def give_user_bonus_for_registration(request):
    """Credit a 200-unit registration bonus to the requesting user's wallet."""
    try:
        user_wallet = UserWallet.objects.get(user=request.user)
        user_wallet.bonus_balance += 200
        user_wallet.save()
        return Response({'success': True}, status=status.HTTP_200_OK)
    except UserWallet.DoesNotExist:
        return Response({'success': False, 'error': 'User wallet not found.'}, status=status.HTTP_404_NOT_FOUND)
