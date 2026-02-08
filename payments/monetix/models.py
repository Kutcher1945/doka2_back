import uuid

from django.db import models


# from authentication.models import CustomUser


class WalletException(models.Model):
    id = models.AutoField(primary_key=True)
    data = models.TextField(default='', blank=True, null=True)
    exception = models.TextField(default='', blank=True, null=True)


class UserWallet(models.Model):
    user = models.ForeignKey("authentication.CustomUser", on_delete=models.CASCADE, null=True, blank=True)

    balance = models.FloatField(default=0, null=True, blank=True)
    bonus_balance = models.FloatField(default=0, null=True, blank=True)
    blocked_balance = models.FloatField(default=0, null=True, blank=True)

    accounts = models.ManyToManyField("UserAccount", blank=True, default=None)
    binance_accounts = models.ManyToManyField("UserBinanceAccount", blank=True, default=None)

    payout_commission = models.FloatField(default=5.0, null=True, blank=True)

    last_refill = models.DateTimeField(auto_now=True, null=True, blank=True)
    wallet_history = models.ManyToManyField("WalletHistory", blank=True, default=None)

    CURRENCY_SYMBOLS = (
        ("USD", "USD"),
        ("UAH", "UAH"),
        ("RUB", "RUB"),
        ("KZT", "KZT"),
        ("UZS", "UZS"),
    )
    currency = models.CharField(default="USD", max_length=100, choices=CURRENCY_SYMBOLS)

    LANGUAGE_SYMBOLS_PAYMENTS = (
        ("en", "en"),
        ("ua", "ua"),
        ("ru", "ru"),
        ("kk", "kk"),
        ("uz", "uz"),
    )
    language_payments = models.CharField(default="en", max_length=100, choices=LANGUAGE_SYMBOLS_PAYMENTS)

    def __str__(self):
        return f"{self.user} "


class WalletHistory(models.Model):
    user_wallet = models.ForeignKey(UserWallet, on_delete=models.SET_NULL, null=True, blank=True)
    pay_time = models.DateTimeField(auto_now_add=True)
    user_account = models.ManyToManyField("UserAccount", blank=True, default=None)
    user_binance_account = models.ManyToManyField("UserBinanceAccount", blank=True, default=None)
    status = models.CharField(max_length=50, null=True, blank=True)
    amount = models.FloatField(null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)
    payment_id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=255)
    method = models.CharField(max_length=10, null=True, blank=True)
    type = models.CharField(max_length=10, null=True, blank=True)
    payout_commission = models.FloatField(default=0.0, null=True, blank=True)

    def __str__(self):
        return f"{self.user_wallet} : {self.payment_id}"


class UserAccount(models.Model):
    user_wallet = models.ForeignKey(UserWallet, on_delete=models.SET_NULL, null=True, blank=True)
    number = models.CharField(max_length=50, null=True, blank=True)
    type = models.CharField(max_length=10, null=True, blank=True)
    card_holder = models.CharField(max_length=150, null=True, blank=True)
    expiry_month = models.CharField(max_length=5, null=True, blank=True)
    expiry_year = models.CharField(max_length=5, null=True, blank=True)
    token = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return f"{self.card_holder} : {self.number}"


class UserBinanceAccount(models.Model):
    user_wallet = models.ForeignKey(UserWallet, on_delete=models.SET_NULL, null=True, blank=True)
    number = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.number}"
