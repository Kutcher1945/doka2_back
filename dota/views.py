import json

from authentication.models import CustomUser
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import IsAuthenticated

from .models import Membership, PlayerInfo, Rating
from .utils import get_game_count, get_floating_commission, get_game_count_to_reduce_commission


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_current_user_lobby(request):
    request_data = request.data
    id_user = request_data.get('id_user')

    user_membership = get_object_or_404(Membership, user__id=id_user)
    data = {'id_lobby': user_membership.lobby.id, 'success': True}
    return JsonResponse(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_game_current_commission(request):
    request_data = request.data
    user_id = request_data.get('user_id')

    game_count = get_game_count(user_id)
    commission = get_floating_commission(game_count)
    games_to_reduce = get_game_count_to_reduce_commission(game_count)

    data = {
        'commission': commission,
        'games_to_reduce': games_to_reduce,
        'game_count': game_count,
        'success': True
    }
    return JsonResponse(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_user(request):
    data = {}

    request_data = request.data
    rates = request_data.get('rates', None)
    id_user = request_data.get('id', None)

    try:
        rate_instances = []
        for rate in rates:
            id_user_rated = rate[0]
            stars = rates[rate]
            rate_instance = Rating(
                rate=stars,
                user=get_object_or_404(CustomUser, id=str(id_user)),
                player_info=get_object_or_404(PlayerInfo, user__id=str(id_user_rated)),
            )
            rate_instances.append(rate_instance)

        Rating.objects.bulk_create(rate_instances)

        player_info_instances = PlayerInfo.objects.filter(user__id__in=[rate[0] for rate in rates]).select_related(
            'user')
        for player_info in player_info_instances:
            game_ratings = player_info.rate.all()
            rate_sum = sum([float(r.rate) for r in game_ratings])
            rate = rate_sum / len(game_ratings)

            user_instance = player_info.user
            user_instance.service_rating = rate
            user_instance.save()

        data['success'] = True
    except Exception as exception:
        print(exception)
        data['success'] = False
        data['err'] = "Something go wrong"
    return JsonResponse(json.dumps(data), safe=False)
