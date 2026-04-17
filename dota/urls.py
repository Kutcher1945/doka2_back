from django.urls import include, path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from .views import get_current_user_lobby, rate_user
from .viewsets import LobbyViewSet, MembershipViewSet, BotViewSet, PlayerInfoViewSet, GameHistoryViewSet
from .utils import get_game_count, get_floating_commission, get_game_count_to_reduce_commission

router = DefaultRouter()
router.register(r'lobby', LobbyViewSet, basename='lobby')
router.register(r'membership', MembershipViewSet, basename='membership')
router.register(r'bot', BotViewSet, basename='bot')
router.register(r'player_info', PlayerInfoViewSet, basename='player_info')
router.register(r'game_history', GameHistoryViewSet, basename='game_history')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def _commission_compat(request):
    """Backward-compat alias for /dota/game_history/commission/"""
    user_id = request.user.id
    game_count = get_game_count(user_id)
    commission = get_floating_commission(game_count)
    games_to_reduce = get_game_count_to_reduce_commission(game_count)
    return Response({
        'commission': commission,
        'games_to_reduce': games_to_reduce,
        'game_count': game_count,
    })


urlpatterns = [
    path('', include(router.urls)),
    path('rate_user/', rate_user),
    path('get_current_user_lobby/', get_current_user_lobby),
    path('get_user_game_current_commission/', _commission_compat),  # backward compat
    path('report/', include('dota.report.urls')),
]
