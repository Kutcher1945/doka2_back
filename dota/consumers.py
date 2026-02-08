import json
import logging

from asgiref.sync import async_to_sync
from authentication.models import CustomUser
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.shortcuts import get_object_or_404
from dota.tasks import controller_dota_task
from payments.monetix.models import UserWallet

from .models import Membership, Lobby, Bot

logging.basicConfig(
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    level=logging.INFO
)


class LobbyConsumer(AsyncWebsocketConsumer):
    """
    LobbyConsumer which supports WebSockets and forwards incoming messages to
    the websocket channels.
    """

    @staticmethod
    def check_membership_status(data: dict) -> dict:
        """Check membership status and return data about status membership"""

        id_user = data['userID']
        id_lobby = data['lobbyID']
        team = data['team']
        user_position = data['userPosition']

        lobby = get_object_or_404(Lobby, id=id_lobby)
        user = get_object_or_404(UserWallet, user__id=id_user)

        if user.user.is_blocked:
            data['error'] = 'user: ' + str(id_user) + ' is_blocked'
            return data

        if lobby.is_slots_lte_memberships:
            data['error'] = 'lobby_full'
            return data

        if Membership.objects.filter(user__id=id_user).exists():
            data['error'] = 'in_lobby'
            return data

        if user.balance < lobby.bet:
            data['error'] = 'balance'
            return data

        if lobby.game_mode == '1v1 Solo Mid':
            existing_user = Membership.objects.filter(lobby=lobby).exclude(user__id=id_user).first()

            if existing_user:
                existing_user_mmr = existing_user.user.dota_mmr

                min_mmr = existing_user_mmr - 1000
                max_mmr = existing_user_mmr + 1000

                if not (min_mmr <= user.user.dota_mmr <= max_mmr):
                    data['error'] = 'out_mmr_range'
                    return data

        Membership.objects.create(
            user=CustomUser.objects.get(id=id_user),
            lobby=lobby,
            team=team,
            position=user_position
        )

        data['success'] = True
        lobby.refresh_from_db()
        if lobby.membership.count() == lobby.slots:
            data['full'] = True

        return data

    def new_membership(self, data):
        data['success'] = False
        new_data = self.check_membership_status(data)
        async_to_sync(self.group_lobby_message)(new_data)

    def remove_membership(self, data):
        id_user = data['userID']
        data['success'] = False

        if member := Membership.objects.filter(user__id=id_user).first():
            member.delete()
            data['success'] = True

        async_to_sync(self.group_lobby_message)(data)

    def status_ready(self, data):
        id_user = data['userID']
        id_lobby = data['lobbyID']

        print("id_user %s" % id_user)
        print("id_lobby %s" % id_lobby)

        Membership.objects.filter(user__id=id_user).update(status=True)
        if Membership.objects.filter(lobby__id=id_lobby, status=False):
            data['status'] = False
            data['success'] = True
            async_to_sync(self.group_lobby_message)(data)
            return

        members = Membership.objects.filter(lobby__id=id_lobby).select_related('user__user_wallet')
        lobby = Lobby.objects.filter(id=id_lobby).first()
        if members.filter(user__user_wallet__balance__lt=lobby.bet):
            data['success'] = False
            data['error'] = 'balance'
            async_to_sync(self.group_lobby_message)(data)
            return

        free_bot = Bot.objects.filter(bot_status=False).first()
        if not free_bot:
            data['status'] = False
            data['success'] = False
            data['error'] = "Bots are busy"
            async_to_sync(self.group_lobby_message)(data)
            return

        for member in members:
            wallet = member.user.user_wallet
            wallet.balance = wallet.balance - lobby.bet
            wallet.blocked_balance = wallet.blocked_balance + lobby.bet
            wallet.save()

        lobby.status = "Pending"
        lobby.save(update_fields=['status'])

        q_lobby_players = members.values_list('user__steam_id')

        free_bot.bot_status = True
        free_bot.save()

        print('PRE START TASK')
        task_id = controller_dota_task.delay(
            lobby.id, lobby.name, lobby.password, list(q_lobby_players), lobby.game_mode,
            free_bot.bot_name, free_bot.bot_password
        )
        print("POST TEST TASK")

        lobby.task_id = task_id
        lobby.save(update_fields=['task_id'])

        data['start_game'] = True
        data['status'] = True
        data['success'] = True

        async_to_sync(self.group_lobby_message)(data)

    commands = {
        'new_membership': new_membership,
        'remove_membership': remove_membership,
        'status_ready': status_ready
    }

    # Consumer connect
    async def connect(self):
        self.lobby_id = self.scope['url_route']['kwargs']['lobby_id']
        self.lobby_group_name = 'lobby_%s' % self.lobby_id

        # Join lobby group
        await self.channel_layer.group_add(
            self.lobby_group_name,
            self.channel_name
        )

        await self.accept()

    # Consumer disconnect
    async def disconnect(self, close_code):
        # Leave lobby group
        await self.channel_layer.group_discard(
            self.lobby_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)

        data = text_data_json['data']

        await database_sync_to_async(self.commands[data['command']])(self, data)

    # Send message to lobby group
    async def group_lobby_message(self, data):
        await self.channel_layer.group_send(
            self.lobby_group_name,
            {
                'type': 'lobby_message',
                'data': data
            }
        )

    # Send message to WebSocket
    async def lobby_message(self, event):
        data = event['data']

        await self.send(text_data=json.dumps({
            'data': data
        }))
