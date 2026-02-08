import json
from datetime import datetime
from typing import Any

import requests
from authentication.models import CustomUser
from django.http import JsonResponse
from dota.models import Lobby
from dota.report.models import ReportUser, ReportLobby
from dota.report.utils import cancel_game, finish_game
from dota.utils import block_or_unblock_lobby
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import IsAuthenticated, AllowAny


@api_view(['POST'])
@permission_classes([AllowAny])
def post_report_result(request: Any) -> JsonResponse:
    """
    POST request which one get data from bitrix and based on the response,
    the lobby distributes the funds, and the user is blocked or removed from him.
    """
    data = {}
    request_data = request.data

    lobby_id = request_data.get('lobby_id', None)
    result = request_data.get('result', None)
    users_reported_data = request_data.get('users_reported_data', None)

    try:
        report_lobby = ReportLobby.objects.get(lobby__id=lobby_id)

        for user_reported_data in users_reported_data:
            report_user = report_lobby.reported_members.get(user_reported__id=user_reported_data["user_id"])
            report_user.result = user_reported_data["result"]
            report_user.datetime_finish = datetime.now()
            report_user.save()

            if user_reported_data["result"] == "guilty":
                user = CustomUser.objects.get(id=user_reported_data["user_id"])
                user.is_blocked = True
                user.datetime_block = datetime.now()
                user.save()

        block_or_unblock_lobby(lobby_id, False)

        if result == "unlock":
            finish_game(lobby_id)
        elif result == "cancel":
            cancel_game(lobby_id)

        report_lobby.result = result
        report_lobby.datetime_finish = datetime.now()
        report_lobby.save()

        data['success'] = True
    except Exception as exception:
        print(exception)
        data['success'] = False
        data['err'] = "Something go wrong"
    return JsonResponse(json.dumps(data), safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_new_player(request: Any) -> JsonResponse:
    """POST request that creates a new reported user and creates a reported lobby if not created"""
    data = {}

    request_data = request.data
    user_id = request_data.get('user_id', None)
    user_reported_id = request_data.get('user_reported_id', None)
    lobby_id = request_data.get('lobby_id', None)
    datetime_create_game_time = request_data.get('datetime_create_game_time', None)

    try:

        try:
            report_lobby = ReportLobby.objects.get(lobby__id=lobby_id)
        except ReportLobby.DoesNotExist:
            report_lobby = ReportLobby.objects.create(
                lobby=Lobby.objects.get(id=lobby_id),
            )

            lobby = Lobby.objects.get(id=lobby_id)
            lobby.is_block = True
            lobby.save()

        reported_user = ReportUser.objects.create(
            user=CustomUser.objects.get(id=user_id),
            user_reported=CustomUser.objects.get(id=user_reported_id),
            datetime_create_game_time=datetime_create_game_time
        )

        report_lobby.reported_members.add(reported_user)
        report_lobby.save()

        data['success'] = True
    except Exception as exception:
        print(exception)
        data['success'] = False
        data['err'] = "Something go wrong"
    return JsonResponse(json.dumps(data), safe=False)
