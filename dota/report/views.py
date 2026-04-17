import logging
from typing import Any

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from authentication.models import CustomUser
from dota.models import Lobby
from dota.report.models import ReportUser, ReportLobby
from dota.report.utils import cancel_game, finish_game
from dota.utils import block_or_unblock_lobby

logger = logging.getLogger(__name__)


def _check_internal_secret(request) -> bool:
    """
    Verify the shared secret header sent by the internal moderation system (Bitrix).
    Configure INTERNAL_API_SECRET in settings/env.
    """
    secret = getattr(settings, 'INTERNAL_API_SECRET', None)
    if not secret:
        return False
    return request.headers.get('X-Internal-Secret') == secret


@api_view(['POST'])
def post_report_result(request: Any) -> JsonResponse:
    """
    Receive moderation verdict from internal system (Bitrix).
    Protected by a shared secret header (X-Internal-Secret).
    Blocks guilty users, then settles or cancels the game.
    """
    if not _check_internal_secret(request):
        return JsonResponse({'success': False, 'error': 'Unauthorized.'}, status=403)

    lobby_id = request.data.get('lobby_id')
    result = request.data.get('result')
    users_reported_data = request.data.get('users_reported_data', [])

    try:
        report_lobby = ReportLobby.objects.get(lobby__id=lobby_id)

        for entry in users_reported_data:
            report_user = report_lobby.reported_members.get(user_reported__id=entry['user_id'])
            report_user.result = entry['result']
            report_user.datetime_finish = timezone.now()
            report_user.save()

            if entry['result'] == 'guilty':
                CustomUser.objects.filter(id=entry['user_id']).update(
                    is_blocked=True,
                    datetime_block=timezone.now(),
                )

        block_or_unblock_lobby(lobby_id, False)

        if result == 'unlock':
            finish_game(lobby_id)
        elif result == 'cancel':
            cancel_game(lobby_id)

        report_lobby.result = result
        report_lobby.datetime_finish = timezone.now()
        report_lobby.save()

        return JsonResponse({'success': True})
    except ReportLobby.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Report not found.'}, status=404)
    except Exception:
        logger.exception('post_report_result failed for lobby %s', lobby_id)
        return JsonResponse({'success': False, 'error': 'Internal error.'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_new_player(request: Any) -> JsonResponse:
    """File a report against another player in a lobby."""
    user_reported_id = request.data.get('user_reported_id')
    lobby_id = request.data.get('lobby_id')
    datetime_create_game_time = request.data.get('datetime_create_game_time')

    try:
        lobby = Lobby.objects.get(id=lobby_id)
        report_lobby, created = ReportLobby.objects.get_or_create(lobby=lobby)
        if created:
            lobby.is_block = True
            lobby.save(update_fields=['is_block'])

        reported_user = ReportUser.objects.create(
            user=request.user,
            user_reported=CustomUser.objects.get(id=user_reported_id),
            datetime_create_game_time=datetime_create_game_time,
        )
        report_lobby.reported_members.add(reported_user)
        report_lobby.save()

        return JsonResponse({'success': True})
    except (Lobby.DoesNotExist, CustomUser.DoesNotExist) as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=404)
    except Exception:
        logger.exception('report_new_player failed')
        return JsonResponse({'success': False, 'error': 'Internal error.'}, status=500)
