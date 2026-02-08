from django.contrib import admin

from .models import UserVerification, VerificationHistory

admin.site.register(UserVerification)
admin.site.register(VerificationHistory)
