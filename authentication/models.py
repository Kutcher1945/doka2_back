from uuid import uuid4

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

from authentication import UserOnlineStatuses
from payments.monetix.models import UserWallet
from . import managers
from .verification.models import UserVerification


class CustomUser(AbstractUser):
    username = models.CharField('username', max_length=100, blank=True)
    email = models.EmailField('email', unique=True)
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'. Up to 15 digits "
                                         "allowed.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True,
                                    unique=True)  # validators should be a list
    ip_address = models.GenericIPAddressField(default='', null=True, blank=True)
    datetime_create = models.DateTimeField(default=timezone.now)
    online_status = models.CharField(choices=UserOnlineStatuses.choices,
                                     default=UserOnlineStatuses.ONLINE,
                                     max_length=255)
    steam_id = models.CharField(null=True, blank=True, max_length=100)
    connected_games = models.ManyToManyField("ConnectedGames", blank=True, default=None)

    dota_game_history = models.ManyToManyField('dota.GameHistory', blank=True, default=None)
    dota_mmr = models.PositiveIntegerField(default=0, null=True, blank=True)
    dota_rank = models.PositiveIntegerField(default=1, null=True, blank=True)

    verification = models.OneToOneField(UserVerification, on_delete=models.CASCADE, null=True, blank=True,
                                        default=None)
    user_wallet = models.ForeignKey(UserWallet, on_delete=models.CASCADE, null=True, blank=True,
                                    default=None)
    service_rating = models.FloatField(validators=[MinValueValidator(1.0), MaxValueValidator(5.0)], null=True,
                                       blank=True, default=5.0)

    is_blocked = models.BooleanField(default=False, blank=True)
    datetime_block = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number']

    objects = managers.CustomUserManager()

    def __str__(self):
        return f"{self.email}"


class RestorePasswordRecord(models.Model):
    user = models.ForeignKey(CustomUser,
                             verbose_name='Пользователь',
                             on_delete=models.CASCADE)
    used = models.BooleanField(default=False,
                               verbose_name='Использован')
    token = models.CharField(default=uuid4,
                             max_length=255)


class ConnectedGames(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name}"
