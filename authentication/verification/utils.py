import random

from django.conf import settings

from authentication.models import CustomUser
from .models import UserVerification


def get_user_verification(custom_user: CustomUser) -> UserVerification:
    """Get or create the UserVerification record for the given user."""
    user_verification, created = UserVerification.objects.get_or_create(user=custom_user)
    if created:
        custom_user.verification = user_verification
        custom_user.save(update_fields=['verification'])
    return user_verification


def generate_verification_id(customer_id: int) -> str:
    return f"{settings.SHUFTIPRO_TRANSACTION_TYPE}_{customer_id}_{random.randint(0, 9999999)}"
