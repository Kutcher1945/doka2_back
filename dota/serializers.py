from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from .models import Lobby, Membership, Bot, PlayerInfo, GameHistory

ALL_FIELDS = '__all__'


class MembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)
    dota_mmr = serializers.IntegerField(source='user.dota_mmr', read_only=True)
    service_rating = serializers.IntegerField(source='user.service_rating', read_only=True)

    class Meta:
        model = Membership
        fields = ('user_id', 'username', 'team', 'position', 'status', 'leader', 'dota_mmr', 'service_rating')


class PlayerInfoSerializer(ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = PlayerInfo
        fields = ('username', 'team', 'id', 'steam_id', 'hero_id', 'team', 'game_team', 'game_name', 'rate')


class LobbySerializerForHistory(ModelSerializer):
    class Meta:
        model = Lobby
        fields = ('id', 'name', 'bet', 'status', 'is_block')


class GameHistorySerializer(ModelSerializer):
    players_info = PlayerInfoSerializer(many=True, required=False)
    lobby = LobbySerializerForHistory(required=False)

    class Meta:
        model = GameHistory
        fields = ('id', 'finish_game', 'result', 'players_info', 'lobby')


class LobbySerializer(ModelSerializer):
    # membership = MembershipSerializer(many=True, required=False)

    class Meta:
        model = Lobby
        fields = ('id', 'name', 'bet', 'lobby_lvl', 'slots', 'game_mode', 'status', 'datetime_start_game', 'is_block')


class BotSerializer(ModelSerializer):
    class Meta:
        model = Bot
        fields = ALL_FIELDS


class MembershipSerializerForCurrentLobby(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField(source='user.user_id')

    class Meta:
        model = Membership
        fields = ('user_id', 'team')


class LobbySerializerForCurrentLobby(serializers.ModelSerializer):
    members = MembershipSerializer(many=True, read_only=True)

    class Meta:
        model = Lobby
        fields = ('id', 'name', 'members')
