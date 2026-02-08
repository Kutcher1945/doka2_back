from datetime import datetime

from core.celery import app
from django.utils import timezone
from dota2.client import Dota2Client
from dota2.common_enums import ESOType
from dota2.features import sharedobjects as so
from dota2.proto_enums import DOTA_GameMode, DOTA_GC_TEAM
from steam.client import SteamClient
from steam.enums import EResult

from .utils import *

logging.basicConfig(
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    level=logging.DEBUG
)


class DotaLobbyManager:
    def __init__(self, lobby_id, lobby_name, lobby_password, q_lobby_players, lobby_game_mode, bot_name, bot_password):
        self.lobby_id = lobby_id
        self.lobby_name = lobby_name
        self.lobby_password = lobby_password
        self.lobby_players = q_lobby_players
        self.lobby_game_mode = lobby_game_mode
        self.bot_name = bot_name
        self.bot_password = bot_password
        self.client = SteamClient()
        self.dota = Dota2Client(self.client)

        # get lobby proto
        CSODOTALobbyProto = so.find_so_proto(ESOType.CSODOTALobby)
        LobbyState = CSODOTALobbyProto.State

        GameHistory.objects.create(
            lobby_link=Lobby.objects.get(id=self.lobby_id),
        )

        # add this callback for event 'lobby_changed'
        # self.client.on('disconnected', self.reconnect_client)
        self.dota.on('lobby_changed', self.lobby_change_handler)
        self.dota.on('ready', self.create_lobby)
        self.dota.on('lobby_new', self.on_lobby_new)

        # lobby state handler dispatch
        self.state_handler_dispatch = dict([
            (LobbyState.UI, self.controller_user_in_ui),
            (LobbyState.READYUP, self.test),
            (LobbyState.NOTREADY, self.test),
            (LobbyState.SERVERSETUP, self.test),
            (LobbyState.RUN, self.test),
            (LobbyState.POSTGAME, self.post_game_handler),
            (LobbyState.SERVERASSIGN, self.test)
        ])

    def main(self):
        logging.info("Starting main")

        if not self.lobby_password:
            self.lobby_password = ""

        if not self.lobby_players:
            raise RuntimeError("No players in lobby!!!")

        try:
            self._cleanup()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

        self._login_in_steam()

        logging.info('Starting Dota 2...')
        self._start_dota()

        self.dota.wait_event('lobby_changed')

        self.client.run_forever()

    def _cleanup(self):
        self.dota.destroy_lobby()
        self.dota.exit()
        self.client.logout()

    def _login_in_steam(self):
        result = self.client.login(self.bot_name, self.bot_password)

        if result != EResult.OK:
            raise RuntimeError("Login failed")

    def _start_dota(self):
        self.dota.launch()

    def stop(self):
        self.client.logout()
        self.dota.exit()

    def lobby_change_handler(self, message):
        logging.info(f"Event: Lobby Change: {message}")

        if message.HasField('state'):
            # call appropriate handler for lobby state
            self.state_handler_dispatch[message.state](message)

    def create_lobby(self):
        self.dota.destroy_lobby()
        logging.info("Creating new lobby... ")

        game_mode_map = {
            "All Pick": DOTA_GameMode.DOTA_GAMEMODE_AP,
            "1v1 Solo Mid": DOTA_GameMode.DOTA_GAMEMODE_1V1MID,
            "Captains Mode": DOTA_GameMode.DOTA_GAMEMODE_CM,
        }

        game_mode = game_mode_map.get(self.lobby_game_mode, DOTA_GameMode.DOTA_GAMEMODE_AP)

        settings = {
            'game_name': self.lobby_name,
            "pass_key": "PWA",
            "game_mode": game_mode,
        }

        self.dota.create_practice_lobby(self.lobby_password, settings)

    def invite_players_to_lobby(self, lobby_players):
        for lobby_player in lobby_players:
            player_id = int(lobby_player[0])
            try:
                logging.info('invite player {}'.format(player_id))
                self.dota.invite_to_lobby(player_id)
            except Exception as exception:
                logging.info(exception)

    def on_lobby_new(self, message):
        settings = {
            'game_name': "CyberT | " + self.lobby_name,
            "allow_spectating": True,
            "pass_key": str(self.lobby_id),
            'server_region': 8  # 3 id Europe, 8 Stockholm server region
        }
        self.dota.config_practice_lobby(settings)

        logging.info('lobby {} created'.format(self.dota.lobby.lobby_id))
        self.invite_players_to_lobby(self.lobby_players)

        self.dota.join_practice_lobby_team(DOTA_GC_TEAM.PLAYER_POOL)

    def test(self, message):
        logging.info(f"Event: State:{self.bot_name} {message.state}")

    def launch_lobby(self):
        logging.info("All players take their side, launch practice lobby")
        lobby = Lobby.objects.get(id=self.lobby_id)
        lobby.datetime_start_game = datetime.now()
        lobby.status = "Game started"
        lobby.save()

        self.dota.launch_practice_lobby()

    def controller_user_in_ui(self, message):
        if message.HasField('state') and message.state != 0:
            return

        logging.info("Game mode: " + str(self.lobby_game_mode))

        good_side, bad_side, position_is_set = check_slots(message, 0, 0, 0)

        if self.lobby_game_mode in (
        "All Pick", "Captains Mode") and good_side == 5 and bad_side == 5 and position_is_set == 10:
            self.launch_lobby()
        elif self.lobby_game_mode == "1v1 Solo Mid" and good_side == 1 and bad_side == 1 and position_is_set == 2:
            self.launch_lobby()

    def post_game_handler(self, message):
        try:
            logging.info(f"message: {message}")

            result = self.get_result_from_match_outcome(message.match_outcome)
            queryset = []
            lobby = Lobby.objects.filter(id=self.lobby_id).first()
            for member in message.all_members[1:]:
                queryset, user_info_from_dota = parse_and_save_steam_massage(member, queryset)
                steam_id, team = user_info_from_dota

                if team in ["DOTA_GC_TEAM_GOOD_GUYS", "DOTA_GC_TEAM_BAD_GUYS"]:
                    user = CustomUser.objects.filter(steam_id=str(steam_id)).first()
                    game_history_instance = GameHistory.objects.get(lobby_link__id=self.lobby_id)

                    if not check_if_lobby_blocked(lobby):
                        distribute_funds_and_mmr(user, lobby, team, result)

                    user.dota_game_history.add(game_history_instance.id)
                    user.save()

            game_history_instance = GameHistory.objects.filter(lobby_link__name=self.lobby_name).first()
            game_history_instance.result = result
            game_history_instance.players_info.set(queryset)
            game_history_instance.save()

            lobby.status = "Finished"
            lobby.datetime_finish_game = timezone.now()
            lobby.game_history = game_history_instance
            lobby.match_id = message.match_id
            lobby.save()

            if lobby.is_block:
                fill_data_about_blocked_users(lobby)
                send_block_info_to_bitrix(lobby)

        except Exception as exception:
            logging.error(f"Exception occurred: {exception}")

        logging.info("Match is over, bot destroy lobby and exit from Dota2 and Steam!")
        self.shutdown_bot()

    @staticmethod
    def get_result_from_match_outcome(match_outcome):
        if match_outcome == 2:
            return "DOTA_GC_TEAM_GOOD_GUYS"
        elif match_outcome == 3:
            return "DOTA_GC_TEAM_BAD_GUYS"
        else:
            return "Unknown"

    def shutdown_bot(self):
        self.dota.remove_all_listeners()
        self.client.remove_all_listeners()
        self.dota.destroy_lobby()
        self.dota.exit()
        self.dota.abandon_current_game()
        self.client.logout()
        self.client.disconnect()
        change_bot_status(self.bot_name, False)
        logging.info("Bot has been shut down.")
        lobby = Lobby.objects.filter(id=self.lobby_id).first()
        app.control.revoke(lobby.task_id, terminate=True)
