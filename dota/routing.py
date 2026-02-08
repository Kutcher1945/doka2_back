from django.urls import re_path, path

from chat.consumers import ChatConsumer
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/lobby/(?P<lobby_id>\w+)/$', consumers.LobbyConsumer.as_asgi()),
    path("", ChatConsumer.as_asgi()),
]
