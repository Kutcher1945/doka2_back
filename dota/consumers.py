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

logger = logging.getLogger(__name__)


class LobbyConsumer(AsyncWebsocketConsumer):

    def check_membership_status(self, data: dict) -> dict:
        """Check membership status using the authenticated user from scope."""
        user = self.scope['user']
        id_lobby = data['lobbyID']
        team = data['team']
        user_position = data['userPosition']

        lobby = get_object_or_404(Lobby, id=id_lobby)
        user_wallet = get_object_or_404(UserWallet, user=user)

        if user.is_blocked:
            data['error'] = 'user_is_blocked'
            return data

        if lobby.is_slots_lte_memberships:
            data['error'] = 'lobby_full'
            return data

        if Membership.objects.filter(user=user).exists():
            data['error'] = 'in_lobby'
            return data

        if user_wallet.balance < lobby.bet:
            data['error'] = 'balance'
            return data

        if lobby.game_mode == '1v1 Solo Mid':
            existing_member = Membership.objects.filter(lobby=lobby).exclude(user=user).first()
            if existing_member:
                existing_user_mmr = existing_member.user.dota_mmr
                min_mmr = existing_user_mmr - 1000
                max_mmr = existing_user_mmr + 1000
                if not (min_mmr <= user.dota_mmr <= max_mmr):
                    data['error'] = 'out_mmr_range'
                    return data

        Membership.objects.create(
            user=user,
            lobby=lobby,
            team=team,
            position=user_position,
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
        user = self.scope['user']
        data['success'] = False

        if member := Membership.objects.filter(user=user).first():
            member.delete()
            data['success'] = True

        async_to_sync(self.group_lobby_message)(data)

    def status_ready(self, data):
        user = self.scope['user']
        id_lobby = data['lobbyID']

        logger.info("status_ready user=%s lobby=%s", user.id, id_lobby)

        Membership.objects.filter(user=user).update(status=True)
        if Membership.objects.filter(lobby__id=id_lobby, status=False).exists():
            data['status'] = False
            data['success'] = True
            async_to_sync(self.group_lobby_message)(data)
            return

        lobby = Lobby.objects.filter(id=id_lobby).first()
        if not lobby:
            data['success'] = False
            data['error'] = 'lobby_not_found'
            async_to_sync(self.group_lobby_message)(data)
            return

        insufficient_balance = UserWallet.objects.filter(
            user__membership__lobby__id=id_lobby,
            balance__lt=lobby.bet,
        ).exists()
        if insufficient_balance:
            data['success'] = False
            data['error'] = 'balance'
            async_to_sync(self.group_lobby_message)(data)
            return

        free_bot = Bot.objects.filter(bot_status=False).first()
        if not free_bot:
            data['status'] = False
            data['success'] = False
            data['error'] = 'Bots are busy'
            async_to_sync(self.group_lobby_message)(data)
            return

        members = Membership.objects.filter(lobby__id=id_lobby).select_related('user')
        for member in members:
            wallet = UserWallet.objects.filter(user=member.user).first()
            if wallet:
                wallet.balance -= lobby.bet
                wallet.blocked_balance += lobby.bet
                wallet.save()

        lobby.status = 'Pending'
        lobby.save(update_fields=['status'])

        q_lobby_players = list(members.values_list('user__steam_id', flat=True))

        free_bot.bot_status = True
        free_bot.save()

        logger.info("Starting game task for lobby %s", lobby.id)
        task_id = controller_dota_task.delay(
            lobby.id, lobby.name, lobby.password, q_lobby_players, lobby.game_mode,
            free_bot.bot_name, free_bot.bot_password,
        )

        lobby.task_id = task_id
        lobby.save(update_fields=['task_id'])

        data['start_game'] = True
        data['status'] = True
        data['success'] = True

        async_to_sync(self.group_lobby_message)(data)

    commands = {
        'new_membership': new_membership,
        'remove_membership': remove_membership,
        'status_ready': status_ready,
    }

    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return

        self.lobby_id = self.scope['url_route']['kwargs']['lobby_id']
        self.lobby_group_name = 'lobby_%s' % self.lobby_id

        await self.channel_layer.group_add(
            self.lobby_group_name,
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'lobby_group_name'):
            await self.channel_layer.group_discard(
                self.lobby_group_name,
                self.channel_name,
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        data = text_data_json['data']
        await database_sync_to_async(self.commands[data['command']])(self, data)

    async def group_lobby_message(self, data):
        await self.channel_layer.group_send(
            self.lobby_group_name,
            {
                'type': 'lobby_message',
                'data': data,
            },
        )

    async def lobby_message(self, event):
        data = event['data']
        await self.send(text_data=json.dumps({'data': data}))
