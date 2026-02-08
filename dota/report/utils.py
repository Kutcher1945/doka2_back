import logging

from dota.models import Lobby
from dota.utils import distribute_funds_back_to_user, distribute_funds_and_mmr

logger = logging.getLogger(__name__)


def finish_game(lobby_id: int) -> None:
    lobby = Lobby.objects.get(id=lobby_id)

    for member in lobby.game_history.players_info.all():
        team = None
        if member.team == "1":
            team = "DOTA_GC_TEAM_GOOD_GUYS"
        elif member.team == "2":
            team = "DOTA_GC_TEAM_BAD_GUYS"

        distribute_funds_and_mmr(member.user, lobby,
                                 team, lobby.game_history.result)


def cancel_game(lobby_id: int) -> None:
    lobby = Lobby.objects.get(id=lobby_id)

    for member in lobby.game_history.players_info.all():
        if not member.user.is_blocked:
            distribute_funds_back_to_user(member.user, lobby)
