from django.contrib import admin

from .models import CustomUser, ConnectedGames, RestorePasswordRecord

admin.site.register(CustomUser)
admin.site.register(ConnectedGames)
admin.site.register(RestorePasswordRecord)
