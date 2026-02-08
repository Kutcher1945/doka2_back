from django.db import models

from dota.models import Lobby


class Accounting(models.Model):
    id = models.AutoField(primary_key=True)

    balance = models.FloatField(default=0, null=True, blank=True)

    def __str__(self):
        return f"{self.balance} "


class AccountingHistory(models.Model):
    id = models.AutoField(primary_key=True)
    accounting = models.ForeignKey(Accounting, on_delete=models.SET_NULL, null=True, blank=True)
    lobby = models.ForeignKey(Lobby, on_delete=models.CASCADE)
    datetime = models.DateTimeField(auto_now_add=True)
    service_earning = models.FloatField(null=True, default=None)
    user = models.ForeignKey("authentication.CustomUser", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.id}"
