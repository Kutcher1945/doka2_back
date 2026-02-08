import logging

from authentication.models import CustomUser
from django.db import models

logger = logging.getLogger(__name__)


class Achievement(models.Model):
    """ These objects are what people are earning """
    name = models.CharField(max_length=75)
    key = models.CharField(max_length=75, unique=True)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(default="", max_length=75)
    bonus = models.IntegerField(default=0)
    callback = models.TextField()

    def __unicode__(self):
        return "Achievement(%s, %s)" % (self.name, self.bonus)


class UserAchievement(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, related_name="user_achievements", on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)
