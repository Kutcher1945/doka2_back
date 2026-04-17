from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import IsAuthenticated

from .models import Membership, PlayerInfo, Rating


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user_lobby(request):
    user_membership = get_object_or_404(Membership, user=request.user)
    return JsonResponse({'id_lobby': user_membership.lobby.id, 'success': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_user(request):
    rates = request.data.get('rates')

    try:
        rate_instances = []
        for id_user_rated, stars in rates.items():
            rate_instances.append(Rating(
                rate=stars,
                user=request.user,
                player_info=get_object_or_404(PlayerInfo, user__id=str(id_user_rated)),
            ))
        Rating.objects.bulk_create(rate_instances, ignore_conflicts=True)

        player_info_instances = PlayerInfo.objects.filter(
            user__id__in=list(rates.keys())
        ).select_related('user')

        for player_info in player_info_instances:
            game_ratings = Rating.objects.filter(player_info=player_info)
            if game_ratings.exists():
                avg_rate = sum(float(r.rate) for r in game_ratings) / game_ratings.count()
                player_info.user.service_rating = avg_rate
                player_info.user.save(update_fields=['service_rating'])

        return JsonResponse({'success': True})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})
