from django.db.models import CharField
from django.db.models.functions import Lower
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from authentication.models import CustomUser
from .models import Lobby, Membership, Bot, GameHistory, PlayerInfo
from .serializers import (
    LobbySerializer, MembershipSerializer, BotSerializer,
    GameHistorySerializer, PlayerInfoSerializer,
    LobbySerializerForCurrentLobby,
)
from .utils import get_game_count, get_floating_commission, get_game_count_to_reduce_commission

CharField.register_lookup(Lower)


class LobbyViewSet(GenericViewSet, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, ListModelMixin):
    """
    Single ViewSet for all Lobby operations.

    Filtering via query params:
      - lobby_name      — partial name match
      - lobby_bet_min   — minimum bet
      - lobby_bet_max   — maximum bet
      - position        — exact position filter

    Extra actions:
      - GET  /lobby/similar/   — find lobbies with bet ±10% of ?bet=, exclude ?id=
      - GET  /lobby/current/   — get the requesting user's current lobby
      - GET  /lobby/{id}/memberships/ — list members of a lobby
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LobbySerializer

    def get_queryset(self):
        qs = Lobby.objects.exclude(status="Finished").order_by('-datetime_create')
        params = self.request.query_params

        name = params.get('lobby_name')
        bet_min = params.get('lobby_bet_min')
        bet_max = params.get('lobby_bet_max')
        position = params.get('position')

        if name:
            qs = qs.filter(name__icontains=name)
        if bet_min:
            try:
                qs = qs.filter(bet__gte=float(bet_min))
            except ValueError:
                pass
        if bet_max:
            try:
                qs = qs.filter(bet__lte=float(bet_max))
            except ValueError:
                pass
        if position:
            qs = qs.filter(position=position)

        return qs

    def create(self, request, *args, **kwargs):
        user = request.user
        if user.is_blocked:
            return Response({'error': 'User is blocked.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            bet = int(request.data.get('bet', 0))
        except (TypeError, ValueError):
            return Response({'error': 'Invalid bet value.'}, status=status.HTTP_400_BAD_REQUEST)
        if bet < 50:
            return Response({'error': 'Minimum bet is 50.'}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def similar(self, request):
        """Lobbies with bet ±10% of the given value, excluding the given lobby id."""
        bet = request.query_params.get('bet')
        exclude_id = request.query_params.get('id')
        if not bet:
            return Response([])
        try:
            bet_int = int(bet)
        except ValueError:
            return Response({'error': 'Invalid bet value.'}, status=status.HTTP_400_BAD_REQUEST)
        margin = (10 * bet_int) / 100.0
        qs = Lobby.objects.filter(
            bet__gte=bet_int - margin,
            bet__lte=bet_int + margin,
            status="Created",
        )
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        return Response(LobbySerializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='current')
    def current_lobby(self, request):
        """Return the lobby the requesting user is currently in."""
        membership = Membership.objects.filter(user=request.user).first()
        if not membership:
            return Response({'error': 'User is not in any lobby.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(LobbySerializerForCurrentLobby(membership.lobby).data)

    @action(detail=True, methods=['get'])
    def memberships(self, request, pk=None):
        """List all memberships for a given lobby."""
        try:
            members = Lobby.objects.get(id=pk).members.all()
        except Lobby.DoesNotExist:
            return Response({'error': 'Lobby not found.'}, status=status.HTTP_404_NOT_FOUND)
        memberships = Membership.objects.filter(user__in=members)
        return Response(MembershipSerializer(memberships, many=True).data)


class MembershipViewSet(GenericViewSet, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, ListModelMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = MembershipSerializer
    queryset = Membership.objects.all()


class BotViewSet(GenericViewSet, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, ListModelMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = BotSerializer
    queryset = Bot.objects.all()


class PlayerInfoViewSet(GenericViewSet, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, ListModelMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = PlayerInfoSerializer
    queryset = PlayerInfo.objects.all()


class GameHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for game history.

    List filtering via query params:
      - id_user  — filter by user id (defaults to requesting user)

    Extra actions:
      - GET /game_history/commission/  — get the requesting user's current commission tier
      - GET /game_history/{id}/by_lobby/ — get game history for a lobby
    """
    permission_classes = [IsAuthenticated]
    serializer_class = GameHistorySerializer

    def get_queryset(self):
        try:
            return self.request.user.dota_game_history.all()
        except Exception:
            return GameHistory.objects.none()

    @action(detail=False, methods=['get'])
    def commission(self, request):
        """Return the requesting user's current commission rate and games needed to reduce it."""
        user_id = request.user.id
        game_count = get_game_count(user_id)
        commission = get_floating_commission(game_count)
        games_to_reduce = get_game_count_to_reduce_commission(game_count)
        return Response({
            'commission': commission,
            'games_to_reduce': games_to_reduce,
            'game_count': game_count,
        })

    @action(detail=True, methods=['get'], url_path='by_lobby')
    def by_lobby(self, request, pk=None):
        """Return the game history record attached to a given lobby."""
        try:
            game_history = Lobby.objects.get(id=pk).game_history
        except Lobby.DoesNotExist:
            return Response({'error': 'Lobby not found.'}, status=status.HTTP_404_NOT_FOUND)
        if game_history is None:
            return Response({'error': 'No game history for this lobby.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(GameHistorySerializer(game_history).data)
