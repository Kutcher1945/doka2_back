from django.contrib.auth.base_user import BaseUserManager
from validate_email import validate_email

from payments.monetix.models import UserWallet


class CustomUserManager(BaseUserManager):
    def create_user(self, email, phone_number, password, **extra_fields):
        if not email:
            raise ValueError('The email must be set')
        email = self.normalize_email(email)
        if not validate_email(email):
            raise ValueError('Invalid emails set')

        if not phone_number:
            raise ValueError('The phone_number must be set')

        user = self.model(email=email, phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save()

        user_wallet = UserWallet.objects.create(
            user=user
        )

        user.user_wallet = user_wallet
        user.save()

        return user

    def create_superuser(self, email, phone_number, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is is_superuser=True')

        return self.create_user(email, phone_number, password, **extra_fields)
