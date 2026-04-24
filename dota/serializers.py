from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from .models import Lobby, Membership, Bot, PlayerInfo, GameHistory


class MembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)
    dota_mmr = serializers.IntegerField(source='user.dota_mmr', read_only=True)
    service_rating = serializers.FloatField(source='user.service_rating', read_only=True)

    class Meta:
        model = Membership
        fields = ('user_id', 'username', 'team', 'position', 'status', 'leader', 'dota_mmr', 'service_rating')


class PlayerInfoSerializer(ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = PlayerInfo
        fields = ('id', 'username', 'team', 'steam_id', 'hero_id', 'game_team', 'game_name', 'rate')


class LobbySerializerForHistory(ModelSerializer):
    class Meta:
        model = Lobby
        fields = ('id', 'name', 'bet', 'status', 'is_block')


class GameHistorySerializer(ModelSerializer):
    players_info = PlayerInfoSerializer(many=True, required=False)
    # source corrected: model field is 'lobby_link', not 'lobby'
    lobby = LobbySerializerForHistory(source='lobby_link', required=False)

    class Meta:
        model = GameHistory
        fields = ('id', 'finish_game', 'result', 'players_info', 'lobby')


class LobbySerializer(ModelSerializer):
    # dota_lobby_id is a 64-bit int that exceeds JS Number.MAX_SAFE_INTEGER — send as string
    dota_lobby_id = serializers.CharField(allow_null=True, read_only=True)

    class Meta:
        model = Lobby
        fields = ('id', 'name', 'bet', 'lobby_lvl', 'slots', 'game_mode', 'status', 'datetime_start_game', 'is_block', 'vs_bots', 'dota_lobby_id', 'bot_steam_id')


class BotSerializer(ModelSerializer):
    class Meta:
        model = Bot
        fields = '__all__'


class MembershipSerializerForCurrentLobby(serializers.ModelSerializer):
    # source corrected: user.id, not user.user_id
    user_id = serializers.ReadOnlyField(source='user.id')

    class Meta:
        model = Membership
        fields = ('user_id', 'team')


class LobbySerializerForCurrentLobby(serializers.ModelSerializer):
    # source corrected: related_name on Membership FK to Lobby is 'membership'
    members = MembershipSerializer(source='membership', many=True, read_only=True)

    class Meta:
        model = Lobby
        fields = ('id', 'name', 'members')
