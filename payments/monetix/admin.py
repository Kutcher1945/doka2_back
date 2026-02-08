from django.contrib import admin

from .models import UserWallet, WalletHistory, WalletException, UserAccount, UserBinanceAccount

admin.site.register(UserWallet)
admin.site.register(WalletHistory)
admin.site.register(WalletException)
admin.site.register(UserAccount)
admin.site.register(UserBinanceAccount)
