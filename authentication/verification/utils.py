import random

from core.settings import *

from authentication.models import CustomUser
from .models import UserVerification


def get_user_verification(custom_user: CustomUser) -> UserVerification:
    """Get user wallet and if not exist create it"""
    try:
        user_verification = UserVerification.objects.get(user=custom_user)
    except UserVerification.DoesNotExist:
        user_verification = UserVerification.objects.create(
            user=custom_user
        )

        custom_user.verification = user_verification
        custom_user.save()

    return user_verification


def generate_verification_id(customer_id: int) -> str:
    return SHUFTIPRO_TRANSACTION_TYPE + "_" + str(customer_id) + "_" + str(random.randint(0, 9999999))
