from django.contrib import admin

from .models import Lobby,  Membership, Bot, GameHistory, PlayerInfo, Rating

admin.site.register(Lobby)
admin.site.register(Membership)
admin.site.register(Bot)
admin.site.register(GameHistory)
admin.site.register(PlayerInfo)
admin.site.register(Rating)
