import json
import logging

from celery.app.control import Control
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.shortcuts import get_object_or_404
from dota.tasks import controller_dota_task
from payments.monetix.models import UserWallet

from core.celery import app as celery_app
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
        # user_wallet = get_object_or_404(UserWallet, user=user)  # TODO: re-enable wallet checks

        if user.is_blocked:
            data['error'] = 'user_is_blocked'
            return data

        # vs_bots: only team 1 slots available, capacity = slots/2
        team_capacity = lobby.slots // 2 if lobby.vs_bots else lobby.slots
        if lobby.membership.count() >= team_capacity:
            data['error'] = 'lobby_full'
            return data

        # vs_bots: force team 1 (Radiant) — no Dire slots for real players
        if lobby.vs_bots:
            team = '1'
            data['team'] = '1'

        if Membership.objects.filter(user=user).exists():
            data['error'] = 'in_lobby'
            return data

        # if user_wallet.balance < lobby.bet:
        #     data['error'] = 'balance'
        #     return data

        if not lobby.vs_bots and lobby.game_mode == '1v1 Solo Mid':
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
        full_threshold = lobby.slots // 2 if lobby.vs_bots else lobby.slots
        if lobby.membership.count() >= full_threshold:
            data['full'] = True

        return data

    async def new_membership(self, data):
        data['success'] = False
        new_data = await database_sync_to_async(self.check_membership_status)(data)
        await self.group_lobby_message(new_data)

    async def remove_membership(self, data):
        user = self.scope['user']
        data['success'] = False

        def _leave_and_reset():
            member = Membership.objects.filter(user=user).first()
            if not member:
                return False
            lobby = member.lobby
            member.delete()

            # If lobby was in Pending/Game started state with a running bot task, cancel it
            if lobby.status in ('Pending',) and lobby.task_id:
                try:
                    celery_app.control.revoke(lobby.task_id, terminate=True)
                except Exception:
                    pass
                if lobby.assigned_bot:
                    lobby.assigned_bot.bot_status = False
                    lobby.assigned_bot.save(update_fields=['bot_status'])

            # Reset lobby and remaining members so others can ready up again
            lobby.status = 'Created'
            lobby.task_id = None
            lobby.assigned_bot = None
            lobby.dota_lobby_id = None
            lobby.save(update_fields=['status', 'task_id', 'assigned_bot', 'dota_lobby_id'])
            Membership.objects.filter(lobby=lobby).update(status=False)
            return True

        changed = await database_sync_to_async(_leave_and_reset)()
        if changed:
            data['success'] = True

        await self.group_lobby_message(data)

    async def status_ready(self, data):
        user = self.scope['user']
        id_lobby = data['lobbyID']

        logger.info("status_ready user=%s lobby=%s", user.id, id_lobby)

        await database_sync_to_async(
            lambda: Membership.objects.filter(user=user).update(status=True)
        )()

        still_waiting = await database_sync_to_async(lambda: (
            Membership.objects.filter(lobby__id=id_lobby, team='1', status=False).exists()
            if Lobby.objects.filter(id=id_lobby).values_list('vs_bots', flat=True).first()
            else Membership.objects.filter(lobby__id=id_lobby, status=False).exists()
        ))()
        if still_waiting:
            data['status'] = False
            data['success'] = True
            await self.group_lobby_message(data)
            return

        lobby = await database_sync_to_async(
            lambda: Lobby.objects.filter(id=id_lobby).first()
        )()
        if not lobby:
            data['success'] = False
            data['error'] = 'lobby_not_found'
            await self.group_lobby_message(data)
            return

        # TODO: re-enable wallet balance check

        free_bot = await database_sync_to_async(
            lambda: Bot.objects.filter(bot_status=False).first()
        )()
        if not free_bot:
            data['status'] = False
            data['success'] = False
            data['error'] = 'Bots are busy'
            await self.group_lobby_message(data)
            return

        members = await database_sync_to_async(
            lambda: list(Membership.objects.filter(lobby__id=id_lobby).select_related('user'))
        )()
        # TODO: re-enable wallet deductions

        await database_sync_to_async(lambda: (
            setattr(lobby, 'status', 'Pending') or lobby.save(update_fields=['status'])
        ))()

        q_lobby_players = await database_sync_to_async(
            lambda: list(Membership.objects.filter(lobby__id=id_lobby).values_list('user__steam_id', flat=True))
        )()

        await database_sync_to_async(lambda: (
            setattr(free_bot, 'bot_status', True) or free_bot.save()
        ))()

        vs_bots = await database_sync_to_async(
            lambda: Lobby.objects.filter(id=id_lobby).values_list('vs_bots', flat=True).first()
        )()

        logger.info("Starting game task for lobby %s vs_bots=%s", lobby.id, vs_bots)
        task_id = await database_sync_to_async(controller_dota_task.delay)(
            lobby.id, lobby.name, lobby.password, q_lobby_players, lobby.game_mode,
            free_bot.bot_name, free_bot.bot_password, bool(vs_bots),
        )

        await database_sync_to_async(lambda: (
            Lobby.objects.filter(id=id_lobby).update(task_id=str(task_id), assigned_bot=free_bot)
        ))()

        data['start_game'] = True
        data['status'] = True
        data['success'] = True
        await self.group_lobby_message(data)

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
        await self.commands[data['command']](self, data)

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
