from django.urls import path

from chat.views import ChatAPIView
from . import views

urlpatterns = [
    path('chat_room', ChatAPIView.as_view()),
    path('', views.chat_room, name='chat_room'),
    path('send_message/', views.send_message, name='send_message'),
    path('receive_message/', views.receive_message, name='receive_message'),
]
