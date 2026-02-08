import json

from django.http import JsonResponse
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import IsAuthenticated

from payments.monetix.models import UserWallet



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def give_user_bonus_for_registration(request):
    data = {}

    id_user = request.data.get('id_user')

    if not id_user:
        data['success'] = False
        data['error'] = 'id_user parameter is missing.'
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_wallet = UserWallet.objects.get(user__id=id_user)
        user_wallet.bonus_balance += 200
        user_wallet.save()
        data['success'] = True
        return Response(data, status=status.HTTP_200_OK)
    except UserWallet.DoesNotExist:
        data['success'] = False
        data['error'] = 'User wallet not found.'
        return Response(data, status=status.HTTP_404_NOT_FOUND)
    except Exception as exception:
        data['success'] = False
        data['error'] = 'Something went wrong.'
        return Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
