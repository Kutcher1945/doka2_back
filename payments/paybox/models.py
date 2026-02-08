from django.db import models
from django.contrib.auth import get_user_model

user = get_user_model()


# Create your models here.
# class Test(models.Model):
#     name = models.TextField(default='', blank=True, null=True)
#     surname = models.TextField(default='', blank=True, null=True)
#
#
# class UserWallet(models.Model):
#     user = models.OneToOneField(user, on_delete=models.CASCADE, related_name='user_wallet')
#     balance = models.IntegerField(default=0)
#     bonus_balance = models.IntegerField(default=0)
#     last_refill = models.DateTimeField(auto_now=True)
#     order_id = models.CharField(max_length=255)
#
#     def create_history(self, count, balance):
#         wallet_history = WalletHistory()
#         wallet_history.user_wallet = self
#         wallet_history.pay_balance = balance
#         wallet_history.ordered = count
#         wallet_history.save()
#
#
# class WalletHistory(models.Model):
#     user_wallet = models.ForeignKey(UserWallet, on_delete=models.SET_NULL, related_name='wallet_history', null=True,
#                                     blank=True)
#     pay_balance = models.IntegerField()
#     ordered = models.PositiveIntegerField(default=1)
#     pay_time = models.DateTimeField(auto_now_add=True)
