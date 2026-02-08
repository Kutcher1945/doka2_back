import logging
import re
from typing import Any, Tuple

import requests
from authentication.models import CustomUser
from django.db import transaction
from dota.report.models import ReportLobby
from payments.monetix.models import UserWallet, WalletHistory

from .models import GameHistory, Lobby, Membership, Bot, PlayerInfo
from accounting.utils import save_accounting_data

logger = logging.getLogger(__name__)


def get_game_count(user_id: int) -> int:
    """
    Get the number of games played by a user between the last payout and the current time.

    Args:
        user_id (int): The ID of the user.

    Returns:
        int: The number of games played.
    """
    last_payout = WalletHistory.objects.filter(user_wallet__user__id=user_id, type='payout', status='success').order_by(
        '-pay_time').first()

    if last_payout is None:
        game_count = GameHistory.objects.filter(players_info__user__id=user_id).count()
    else:
        game_count = GameHistory.objects.filter(players_info__user__id=user_id,
                                                finish_game__gt=last_payout.pay_time).count()

    print("game_count: %s " % game_count)
    return game_count


def get_floating_commission(game_count: int) -> float:
    """
    Get the floating commission based on the number of games played.

    Args:
        game_count (int): The number of games played.

    Returns:
        float: The floating commission percentage.
    """
    if game_count < 3 or game_count is None:
        commission = 15.0
    elif game_count < 6:
        commission = 10.0
    else:
        commission = 5.0
    print("commission: %s " % commission)

    return commission


def get_game_count_to_reduce_commission(game_count: int) -> int:
    """
    Get the number of games a user needs to play to reduce the commission.

    Args:
        game_count (int): The amount of the user games.

    Returns:
        int: The number of games needed to reduce the commission.
    """

    if game_count < 3 or game_count is None:
        games_to_reduce = 3 - game_count
    elif game_count < 6:
        games_to_reduce = 6 - game_count
    else:
        games_to_reduce = -1  # Commission already reduced
    print("games_to_reduce: %s " % games_to_reduce)

    return games_to_reduce


def calculate_dota_rank(dota_mmr: int) -> int:
    """Calculation user dota2 rank using his mmr."""
    dota_rank = None

    if 0 <= dota_mmr <= 99:
        dota_rank = 1
    elif 100 <= dota_mmr <= 199:
        dota_rank = 2
    elif 200 <= dota_mmr <= 299:
        dota_rank = 3
    elif 300 <= dota_mmr <= 399:
        dota_rank = 4
    elif 400 <= dota_mmr <= 499:
        dota_rank = 5
    elif 500 <= dota_mmr <= 599:
        dota_rank = 6
    elif 600 <= dota_mmr <= 699:
        dota_rank = 7
    elif 700 <= dota_mmr <= 799:
        dota_rank = 8
    elif 800 <= dota_mmr <= 899:
        dota_rank = 9
    elif 900 <= dota_mmr:
        dota_rank = 10

    return dota_rank


def check_if_user_finished_calibration(user: "authentication.CustomUser") -> bool:
    """Check if user played 10 or more games, than user is calibrated"""
    return user.dota_game_history.count() >= 10


def check_if_user_team_win(team: str, result: str) -> bool:
    """Check if user team win game, checking game result"""
    return str(team) == str(result)


def block_or_unblock_lobby(lobby_id: int, is_blocked: bool) -> None:
    lobby = Lobby.objects.get(id=lobby_id)
    lobby.block = is_blocked
    lobby.save()


def check_if_lobby_blocked(lobby: Lobby) -> bool:
    return lobby.is_block


def distribute_funds_back_to_user(user: UserWallet, lobby: Lobby) -> None:
    """Distribute funds to user back after game"""
    try:
        user.balance = user.balance + lobby.bet
        user.blocked_balance = user.blocked_balance - lobby.bet
        user.save()
    except Exception as exception:
        print(exception)


def distribute_funds_and_mmr(user: CustomUser, lobby: Lobby, team: str, result: str) -> None:
    """
    Distribute funds and mmr to user based on calibrated user or not, user team win or lose.
    Values for MRR and formulas for allocation of funds are taken from company calculations.
    """
    try:
        calibration_is_finished = check_if_user_finished_calibration(user)

        user_team_is_win = check_if_user_team_win(team, result)
        print("user_team_is_win %s" % user_team_is_win)

        with transaction.atomic():
            user_wallet = UserWallet.objects.get(user=user)

            if user_team_is_win:
                game_count = get_game_count(user.id)
                commission = get_floating_commission(game_count)
                commission_amount = (lobby.bet * 2) * (commission / 100)
                save_accounting_data(lobby, user, commission_amount)
                user_wallet.balance = user_wallet.balance + ((lobby.bet * 2) - commission_amount)
                user_wallet.blocked_balance = user_wallet.blocked_balance - lobby.bet

                if calibration_is_finished:
                    user.dota_mmr = user.dota_mmr + 15
                else:
                    user.dota_mmr = user.dota_mmr + 30

            else:
                user_wallet.blocked_balance = user_wallet.blocked_balance - lobby.bet

                if calibration_is_finished:
                    if user.dota_mmr >= 10:
                        user.dota_mmr = user.dota_mmr - 10
                    else:
                        user.dota_mmr = 0
                else:
                    if user.dota_mmr >= 20:
                        user.dota_mmr = user.dota_mmr - 20
                    else:
                        user.dota_mmr = 0

            user_wallet.save()

            dota_rank = calculate_dota_rank(user.dota_mmr)
            user.dota_rank = dota_rank
            user.save()
    except Exception as exception:
        print(exception)


def match_steam_message(pattern_to_match: str, member: Any) -> str:
    """Match pattern from steam message, to get data like: team or steam_id"""
    pattern = re.compile(pattern_to_match + r': (.*)')
    matches = pattern.finditer(str(member))
    result = next(matches, "")
    if result:
        result = result.group(1)
        logging.info(f"{pattern_to_match}: {result}")
    return result


def check_slots(message: Any, good_side: int, bad_side: int, position_is_set: int) -> Tuple[int, int, int]:
    """Check how many slots are occupied for each team"""
    for member in message.all_members[1:]:
        steam_id = match_steam_message("id", member)
        team = match_steam_message("team", member)
        slot = match_steam_message("slot", member)

        membership = Membership.objects.filter(user__steam_id=str(steam_id)).first()

        site_team = ""
        if membership:
            site_team = "DOTA_GC_TEAM_GOOD_GUYS" if membership.team == "1" else "DOTA_GC_TEAM_BAD_GUYS"

            if str(site_team) == str(team):
                if str(team) == "DOTA_GC_TEAM_GOOD_GUYS":
                    good_side += 1
                elif str(team) == "DOTA_GC_TEAM_BAD_GUYS":
                    bad_side += 1

                if slot == str(membership.position):
                    position_is_set += 1

    return good_side, bad_side, position_is_set


def change_bot_status(bot_name: str, status: bool) -> None:
    """Using bot name change its status"""
    Bot.objects.filter(bot_name=bot_name).update(bot_status=status)


def parse_and_save_steam_massage(member: Any, queryset: list) -> Tuple[list, list]:
    """Getting member and parse information about his game from steam message and save it to model"""
    steam_id = match_steam_message("id", member)
    hero_id = match_steam_message("hero_id", member)
    team = match_steam_message("team", member)
    name = match_steam_message("name", member)

    if hero_id == "":
        hero_id = 0  # hero_id 0, so the hero is not choose

    try:
        membership = Membership.objects.filter(user__steam_id=str(steam_id)).first()

        player_info_instance = PlayerInfo.objects.create(
            steam_id=str(steam_id),
            hero_id=str(hero_id),
            game_team=str(team),
            game_name=str(name),
            team=str(membership.team),
            user=membership.user,
        )
        membership.delete()

        queryset.append(player_info_instance)

    except Exception as exception:
        print(exception)

    user_info_from_dota = [steam_id, team]
    return queryset, user_info_from_dota


def send_block_info_to_bitrix(lobby: Lobby) -> None:
    URL = "https://1kz.site/bitrix/rid13/support/index.php"

    reported_members = ReportLobby.objects.get(lobby=lobby).reported_members.all()
    users_reported_data = []

    for reported_member in reported_members:
        try:
            user_reported_data = {'user_id': reported_member.user_reported.id,
                                  'steam_id': reported_member.steam_id_converted,
                                  'hero_id': reported_member.hero_id,
                                  'datetime_create_game_time': reported_member.datetime_create_game_time}
            users_reported_data.append(user_reported_data)
        except Exception as exception:
            print(exception)

    DATA = {
        'lobby_id': lobby.id,
        'dota_lobby_id': lobby.match_id,
        'users_reported_data': users_reported_data,
    }
    print("DATA: %s" % DATA)

    headers = {"Content-Type": "application/json"}
    r = requests.request("POST", URL, json=DATA, headers=headers)

    response = r.text
    print("Response from bitrix from lobby: '{0}' : '{1}'".format(lobby, response))


def fill_data_about_blocked_users(lobby: Lobby) -> None:
    reported_members = ReportLobby.objects.get(lobby=lobby).reported_members.all()
    game_history = GameHistory.objects.get(lobby_link=lobby)

    for reported_member in reported_members:
        # member = game_history.players_info.get(user=reported_member.user)  # test
        member = game_history.players_info.get(user=reported_member.user_reported)  # production
        reported_member.hero_id = member.hero_id
        reported_member.steam_id = member.steam_id
        reported_member.steam_id_converted = int(member.steam_id) - 76561197960265728  # Magic number from Steam
        reported_member.save()
