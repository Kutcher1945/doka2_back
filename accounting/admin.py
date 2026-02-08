from django.contrib import admin

from .models import Accounting, AccountingHistory

admin.site.register(Accounting)
admin.site.register(AccountingHistory)
