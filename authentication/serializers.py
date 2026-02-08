from drf_writable_nested import WritableNestedModelSerializer
from rest_framework import serializers, validators

from payments.monetix.serializers import UserWalletSerializer
from .models import CustomUser, ConnectedGames
from .verification.serializers import UserVerificationSerializerOnlyIsVerified

ALL_FIELDS = '__all__'


class ConnectedGamesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectedGames
        fields = ALL_FIELDS


class CustomUserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False)

    email = serializers.CharField(
        write_only=True, validators=[validators.UniqueValidator(
            message='Эта почта уже существует',
            queryset=CustomUser.objects.all()
        )]
    )
    phone_number = serializers.CharField(
        write_only=True, validators=[validators.UniqueValidator(
            message='This phone number already exists',
            queryset=CustomUser.objects.all()
        )]
    )

    password = serializers.CharField(write_only=True, required=False)
    user_wallet = UserWalletSerializer(required=False)

    connected_games = ConnectedGamesSerializer(required=False)

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'phone_number', 'connected_games', 'username',
                  'datetime_create', 'online_status', 'steam_id', 'dota_mmr', 'dota_rank',
                  'service_rating', 'is_blocked', 'user_wallet', 'password')


class CustomUserRetrieveSerializer(WritableNestedModelSerializer, serializers.ModelSerializer):
    user_wallet = UserWalletSerializer(required=False)
    email = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    connected_games = ConnectedGamesSerializer(many=True, required=False)
    password = serializers.CharField(write_only=True, required=False)
    verification = UserVerificationSerializerOnlyIsVerified(required=False)

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'phone_number', 'connected_games', 'username', 'verification',
                  'datetime_create', 'online_status', 'steam_id', 'dota_mmr', 'dota_rank',
                  'service_rating', 'is_blocked', 'user_wallet', 'verification', 'password')
