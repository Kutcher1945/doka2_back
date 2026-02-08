from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import *
from .viewsets import *

router = DefaultRouter()
router.register(r'lobby_filtered', LobbyViewSetFiltered, basename='lobby_filtered')
router.register(r'lobbies_position', LobbyViewSetPosition, basename='lobby-position')
router.register(r'lobby', LobbyViewSet, basename='lobby')
router.register(r'lobby_similar', LobbyViewSetSimilar, basename='lobby_similar')
router.register(r'membership', MembershipViewSet, basename='membership')
router.register(r'bot', BotViewSet, basename='bot')
router.register(r'player_info', PlayerInfoViewSet, basename='player_info')
router.register(r'game_history', GameHistoryViewSet, basename='game_history')

urlpatterns = [
    path('', include(router.urls)),
    path('rate_user/', rate_user),
    path('report/', include('dota.report.urls')),
    path('get_user_game_current_commission/', get_user_game_current_commission),
]
