from authentication.models import CustomUser
from django.db.models import CharField
from django.db.models.functions import Lower
from django.http import Http404
from rest_framework import permissions, status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.mixins import (
    CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
)
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .models import Lobby, Membership, Bot, GameHistory, PlayerInfo
from .serializers import LobbySerializer, MembershipSerializer, BotSerializer, GameHistorySerializer, \
    PlayerInfoSerializer, LobbySerializerForCurrentLobby, MembershipSerializerForCurrentLobby

CharField.register_lookup(Lower)


class LobbyViewSetFiltered(GenericViewSet,  # generic view functionality
                           CreateModelMixin,  # handles POSTs
                           RetrieveModelMixin,  # handles GETs for 1 Company
                           UpdateModelMixin,  # handles PUTs and PATCHes
                           ListModelMixin):  # handles GETs for many Companies

    permission_classes = (permissions.AllowAny,)
    queryset = Lobby.objects.filter(status="Created")
    serializer_class = LobbySerializer
    pagination_class = LimitOffsetPagination

    def get_filtered_lobbies(self):
        # Retrieve input values from request
        lobby_name = self.request.GET.get('lobby_name')
        lobby_bet_min = float(self.request.GET.get('lobby_bet_min', 0))
        lobby_bet_max = float(self.request.GET.get('lobby_bet_max', float('inf')))
        lobby_player_amount = int(self.request.GET.get('lobby_player_amount', 0))
        offset = int(self.request.GET.get('offset', 0))
        amount = int(self.request.GET.get('amount', 0))
        position = int(self.request.GET.get('position', 0))

        # Build queryset based on input values
        if lobby_name is not None:
            self.queryset = self.queryset.filter(name__icontains=lobby_name)
        if lobby_bet_min is not None:
            self.queryset = self.queryset.filter(bet__gte=lobby_bet_min)
        if lobby_bet_max is not None:
            self.queryset = self.queryset.filter(bet__lte=lobby_bet_max)
        if lobby_player_amount is not None:
            self.queryset = self.queryset.filter(members=lobby_player_amount)
        if position is not None:
            self.queryset = self.queryset.filter(position=position)
        if not position and not lobby_player_amount:
            self.queryset = self.queryset.order_by('-members')

        # Paginate queryset
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(self.queryset, self.request)
        serializer = self.get_serializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


class LobbyViewSet(GenericViewSet,  # generic view functionality
                   CreateModelMixin,  # handles POSTs
                   RetrieveModelMixin,  # handles GETs for 1 Company
                   UpdateModelMixin,  # handles PUTs and PATCHes
                   ListModelMixin):  # handles GETs for many Companies
    permission_classes = (permissions.AllowAny,)
    serializer_class = LobbySerializer
    queryset = Lobby.objects.all()

    def create(self, request, *args, **kwargs):
        user_id = request.data.get('leader')
        bet = request.data.get('bet')
        user = CustomUser.objects.get(id=user_id)

        if user.is_blocked:
            return Response({'error': 'User is blocked.'}, status=status.HTTP_403_FORBIDDEN)
        if int(bet) < 50:
            return Response({'error': 'Min bet 50'}, status=status.HTTP_403_FORBIDDEN)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['get'])
    def memberships(self, request, pk=None):
        try:
            members = Lobby.objects.get(id=pk).members.all()
            memberships = Membership.objects.filter(user__in=members)
            serializer = MembershipSerializer(memberships.all(), many=True)
            return Response(serializer.data)
        except Lobby.DoesNotExist:
            return Response({'error': 'Lobby not found.'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def current_lobby(self, request, pk=None):
        try:
            memberships = Membership.objects.filter(user_id=pk)
            if not memberships:
                return Response({'error': 'User not found in any lobby.'}, status=status.HTTP_204_NO_CONTENT)

            lobby_id = memberships[0].lobby.id
            lobby = Lobby.objects.get(id=lobby_id)

            lobby_serializer = LobbySerializerForCurrentLobby(lobby)
            data = {
                'lobby': lobby_serializer.data,
            }
            return Response(data)
        except Lobby.DoesNotExist:
            return Response({'error': 'Lobby not found.'}, status=status.HTTP_204_NO_CONTENT)


class LobbyViewSetSimilar(GenericViewSet,  # generic view functionality
                          CreateModelMixin,  # handles POSTs
                          RetrieveModelMixin,  # handles GETs for 1 Company
                          UpdateModelMixin,  # handles PUTs and PATCHes
                          ListAPIView):  # handles GETs for many Companies
    permission_classes = (permissions.AllowAny,)
    queryset = None
    serializer_class = LobbySerializer

    def get_queryset(self):
        queryset = None
        bet = self.request.query_params.get('bet')
        id_lobby = self.request.query_params.get('id')
        if bet is not None:
            try:
                bet_int = int(bet)
                percent_from_bet = (10 * bet_int) / 100.0
                queryset = Lobby.objects.filter(
                    bet__gte=bet_int - percent_from_bet,
                    bet__lte=bet_int + percent_from_bet,
                    status="Created"
                ).exclude(id=id_lobby)
            except (TypeError, ValueError):
                pass
        return queryset


class LobbyViewSetPosition(GenericViewSet, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, ListModelMixin):
    permission_classes = (permissions.AllowAny,)
    queryset = Lobby.objects.filter(status="Created")
    serializer_class = LobbySerializer

    def list(self, request, *args, **kwargs):
        position = self.request.query_params.get('position')
        lobbies = self.get_queryset().filter(position=position)
        serializer = self.get_serializer(lobbies, many=True)
        return Response(serializer.data)


class MembershipViewSet(GenericViewSet,  # generic view functionality
                        CreateModelMixin,  # handles POSTs
                        RetrieveModelMixin,  # handles GETs for 1 Company
                        UpdateModelMixin,  # handles PUTs and PATCHes
                        ListModelMixin):  # handles GETs for many Companies

    permission_classes = (permissions.AllowAny,)
    serializer_class = MembershipSerializer
    queryset = Membership.objects.all()


class BotViewSet(GenericViewSet,  # generic view functionality
                 CreateModelMixin,  # handles POSTs
                 RetrieveModelMixin,  # handles GETs for 1 Company
                 UpdateModelMixin,  # handles PUTs and PATCHes
                 ListModelMixin):  # handles GETs for many Companies
    permission_classes = (permissions.AllowAny,)
    serializer_class = BotSerializer
    queryset = Bot.objects.all()


class PlayerInfoViewSet(GenericViewSet,  # generic view functionality
                        CreateModelMixin,  # handles POSTs
                        RetrieveModelMixin,  # handles GETs for 1 Company
                        UpdateModelMixin,  # handles PUTs and PATCHes
                        ListModelMixin):  # handles GETs for many Companies
    permission_classes = (permissions.AllowAny,)
    serializer_class = PlayerInfoSerializer
    queryset = PlayerInfo.objects.all()


class GameHistoryViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.AllowAny,)
    serializer_class = GameHistorySerializer
    queryset = None

    def get_queryset(self):
        """
        Get user_verification by id_user
        """

        id_user = self.request.GET.get('id_user')
        if not id_user:
            raise Http404('id_user parameter is missing.')

        queryset = CustomUser.objects.get(id=id_user).dota_game_history.all()
        return queryset

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        try:
            game_history = CustomUser.objects.get(id=pk).dota_game_history.all()
            serializer = GameHistorySerializer(game_history.all(), many=True)
            return Response(serializer.data)
        except (CustomUser.DoesNotExist, GameHistory.DoesNotExist):
            return Response({'error': 'User or game history not found.'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def current_lobby_game_history(self, request, pk=None):
        try:
            memberships = Membership.objects.filter(user_id=pk)
            if not memberships:
                return Response({'error': 'User not found in any lobby.'}, status=status.HTTP_204_NO_CONTENT)

            lobby_id = memberships[0].lobby.id
            game_history = Lobby.objects.get(id=lobby_id).game_history

            game_history_serializer = GameHistorySerializer(game_history)
            data = {
                'game_history': game_history_serializer.data,
            }
            return Response(data)
        except Lobby.DoesNotExist:
            return Response({'error': 'GameHistory not found.'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def by_lobby_id(self, request, pk=None):
        try:
            game_history = Lobby.objects.get(id=pk).game_history

            game_history_serializer = GameHistorySerializer(game_history)
            data = {
                'game_history': game_history_serializer.data,
            }
            return Response(data)
        except Lobby.DoesNotExist:
            return Response({'error': 'GameHistory not found.'}, status=status.HTTP_204_NO_CONTENT)
