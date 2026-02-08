import logging
from django.utils import timezone

from django.db import models

from authentication.models import CustomUser
from dota.models import Lobby

logger = logging.getLogger(__name__)


class ReportLobby(models.Model):
    id = models.AutoField(primary_key=True)
    lobby = models.ForeignKey(Lobby, on_delete=models.CASCADE)
    reported_members = models.ManyToManyField("ReportUser", blank=True, default=None)

    RESULT_STATUS = (
        ("None", "None"),
        ("unlock", "Finish game"),
        ("cancel", "Cancel game"),
    )
    result = models.CharField(default="None", max_length=100, choices=RESULT_STATUS)

    datetime_create = models.DateTimeField(default=timezone.now)
    datetime_finish = models.DateTimeField(null=True, blank=True)


class ReportUser(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(CustomUser, related_name="user_who_reported", on_delete=models.CASCADE)
    user_reported = models.ForeignKey(CustomUser, related_name="user_reported", on_delete=models.CASCADE)

    hero_id = models.IntegerField(null=True, blank=True)
    steam_id = models.CharField(null=True, blank=True, max_length=100)
    steam_id_converted = models.CharField(null=True, blank=True, max_length=100)

    RESULT_STATUS = (
        ("None", "None"),
        ("not guilty", "Not guilty"),
        ("guilty", "Guilty"),
    )
    result = models.CharField(default="None", max_length=100, choices=RESULT_STATUS)

    datetime_create = models.DateTimeField(default=timezone.now)
    datetime_create_game_time = models.CharField(null=True, blank=True, max_length=100)
    datetime_finish = models.DateTimeField(null=True, blank=True)
