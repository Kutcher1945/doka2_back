from drf_writable_nested import WritableNestedModelSerializer
from rest_framework import serializers, validators

from payments.monetix.serializers import UserWalletSerializer
from .models import CustomUser, ConnectedGames
from .verification.serializers import UserVerificationSerializerOnlyIsVerified


class ConnectedGamesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectedGames
        fields = '__all__'


class CustomUserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False)

    email = serializers.CharField(
        write_only=True,
        validators=[validators.UniqueValidator(
            message='Эта почта уже существует',
            queryset=CustomUser.objects.all(),
        )]
    )
    # required=False: phone is optional at registration
    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        validators=[validators.UniqueValidator(
            message='This phone number already exists',
            queryset=CustomUser.objects.filter(phone_number__isnull=False).exclude(phone_number=''),
        )]
    )
    password = serializers.CharField(write_only=True, required=False)
    # userwallet_set is the reverse FK from UserWallet.user; many=False since each user has one wallet
    user_wallet = UserWalletSerializer(source='userwallet_set', read_only=True, many=False, required=False, default=None)
    connected_games = ConnectedGamesSerializer(many=True, required=False)

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'phone_number', 'connected_games', 'username',
            'datetime_create', 'online_status', 'steam_id', 'dota_mmr', 'dota_rank',
            'service_rating', 'is_blocked', 'user_wallet', 'password',
        )


class CustomUserRetrieveSerializer(WritableNestedModelSerializer, serializers.ModelSerializer):
    user_wallet = UserWalletSerializer(source='userwallet_set', read_only=True, many=False, required=False, default=None)
    email = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    connected_games = ConnectedGamesSerializer(many=True, required=False)
    password = serializers.CharField(write_only=True, required=False)
    verification = UserVerificationSerializerOnlyIsVerified(required=False)

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'phone_number', 'connected_games', 'username', 'verification',
            'datetime_create', 'online_status', 'steam_id', 'dota_mmr', 'dota_rank',
            'service_rating', 'is_blocked', 'user_wallet', 'password',
        )
