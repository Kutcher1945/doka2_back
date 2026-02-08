from rest_framework.serializers import ModelSerializer
from .models import *

# User = get_user_model()


# class UserWalletSerializer(ModelSerializer):
#     class Meta:
#         model = UserWallet
#         fields = ('pk', 'balance', 'bonus_balance')
#
#
# class UserPayBoxSerializer(ModelSerializer):
#     user_wallet = UserWalletSerializer()
#
#     class Meta:
#         model = User
#         fields = ('pk', 'user_wallet')
