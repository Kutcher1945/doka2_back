import threading
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

LOBBY_JOIN_TIMEOUT_SECONDS = 900  # 15 minutes — auto-close if players never join

logging.basicConfig(
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    level=logging.DEBUG
)


class DotaLobbyManager:
    def __init__(self, lobby_id, lobby_name, lobby_password, q_lobby_players, lobby_game_mode, bot_name, bot_password, vs_bots=False):
        self.lobby_id = lobby_id
        self.lobby_name = lobby_name
        self.lobby_password = lobby_password
        self.lobby_players = q_lobby_players
        self.lobby_game_mode = lobby_game_mode
        self.bot_name = bot_name
        self.bot_password = bot_password
        self.vs_bots = vs_bots
        self.client = SteamClient()
        self.dota = Dota2Client(self.client)

        self._timeout_timer: threading.Timer | None = None
        self._game_launched = False
        self._shutdown_called = False

        # get lobby proto
        CSODOTALobbyProto = so.find_so_proto(ESOType.CSODOTALobby)
        LobbyState = CSODOTALobbyProto.State

        self.game_history = GameHistory.objects.create(
            lobby_link=Lobby.objects.get(id=self.lobby_id),
        )

        self.client.on('disconnected', self._on_disconnected)
        self.dota.on('lobby_changed', self.lobby_change_handler)
        self.dota.on('ready', self.create_lobby)
        self.dota.on('lobby_new', self.on_lobby_new)

        self.state_handler_dispatch = {
            LobbyState.UI: self.controller_user_in_ui,
            LobbyState.READYUP: self._log_state,
            LobbyState.NOTREADY: self._log_state,
            LobbyState.SERVERSETUP: self._log_state,
            LobbyState.RUN: self._log_state,
            LobbyState.POSTGAME: self.post_game_handler,
            LobbyState.SERVERASSIGN: self._log_state,
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

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
        logging.info("Steam login result: %s", result)

        if result == EResult.AccountLoginDeniedNeedTwoFactor:
            raise RuntimeError("Login failed: Steam Guard (Mobile Authenticator) is enabled.")
        if result in (EResult.AccountLogonDeniedVerifiedEmailRequired, EResult.AccountLogonDenied):
            raise RuntimeError("Login failed: Steam Guard (Email) is enabled.")
        if result != EResult.OK:
            raise RuntimeError(f"Login failed: {result}")

    def _start_dota(self):
        self.dota.launch()

    def stop(self):
        self.client.logout()
        self.dota.exit()

    # ── Reconnect / error handling ─────────────────────────────────────────────

    def _on_disconnected(self):
        logging.warning("Steam disconnected for bot %s lobby %s", self.bot_name, self.lobby_id)
        self._finalize_lobby('Error', 'steam_disconnected')
        self.shutdown_bot()

    # ── Timeout watchdog ───────────────────────────────────────────────────────

    def _start_join_timeout(self):
        self._timeout_timer = threading.Timer(LOBBY_JOIN_TIMEOUT_SECONDS, self._on_join_timeout)
        self._timeout_timer.daemon = True
        self._timeout_timer.start()
        logging.info("Join timeout started (%ds) for lobby %s", LOBBY_JOIN_TIMEOUT_SECONDS, self.lobby_id)

    def _cancel_timeout(self):
        if self._timeout_timer:
            self._timeout_timer.cancel()
            self._timeout_timer = None

    def _on_join_timeout(self):
        if not self._game_launched:
            logging.warning("Lobby join timeout — no one joined in time. Lobby %s", self.lobby_id)
            self._finalize_lobby('Error', 'join_timeout')
            self.shutdown_bot()

    # ── Lobby event handlers ───────────────────────────────────────────────────

    def lobby_change_handler(self, message):
        logging.info(f"Event: Lobby Change: {message}")
        try:
            if message.HasField('state'):
                handler = self.state_handler_dispatch.get(message.state)
                if handler:
                    handler(message)
                else:
                    logging.warning("Unknown lobby state: %s", message.state)
        except Exception:
            logging.exception("Error in lobby_change_handler")

    def create_lobby(self):
        self.dota.destroy_lobby()
        logging.info("Creating new lobby...")

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
        for steam_id in lobby_players:
            try:
                player_id = int(steam_id)
                logging.info('invite player %s', player_id)
                self.dota.invite_to_lobby(player_id)
            except Exception:
                logging.exception("Failed to invite player %s", steam_id)

    def on_lobby_new(self, message):
        game_mode_map = {
            "All Pick": DOTA_GameMode.DOTA_GAMEMODE_AP,
            "1v1 Solo Mid": DOTA_GameMode.DOTA_GAMEMODE_1V1MID,
            "Captains Mode": DOTA_GameMode.DOTA_GAMEMODE_CM,
        }
        settings = {
            'game_name': "CyberT | " + self.lobby_name,
            "allow_spectating": True,
            "pass_key": str(self.lobby_id),
            'server_region': 8,
            'game_mode': game_mode_map.get(self.lobby_game_mode, DOTA_GameMode.DOTA_GAMEMODE_AP),
        }

        if self.vs_bots:
            # fill_with_bots is the only way to spawn bots in practice lobbies.
            # For 1v1 Solo Mid, 5 bots appear on Dire but game ends on first blood/tower — outcome is correct.
            settings['fill_with_bots'] = True
            settings['bot_difficulty_dire'] = 2    # BOT_DIFFICULTY_MEDIUM
            settings['bot_difficulty_radiant'] = 5  # BOT_DIFFICULTY_INVALID = no Radiant bots
            settings['bot_radiant'] = 0

        self.dota.config_practice_lobby(settings)

        dota_lobby_id = message.lobby_id
        bot_steam_id = str(self.client.steam_id.as_64)
        logging.info('lobby %s created (vs_bots=%s) bot_steam_id=%s', dota_lobby_id, self.vs_bots, bot_steam_id)
        Lobby.objects.filter(id=self.lobby_id).update(dota_lobby_id=dota_lobby_id, bot_steam_id=bot_steam_id)
        self.invite_players_to_lobby(self.lobby_players)
        self.dota.join_practice_lobby_team(DOTA_GC_TEAM.PLAYER_POOL)

        self._start_join_timeout()

    def _log_state(self, message):
        logging.info("Event: State:%s %s", self.bot_name, message.state)

    def launch_lobby(self):
        logging.info("All players in position — launching practice lobby")
        self._game_launched = True
        self._cancel_timeout()

        lobby = Lobby.objects.get(id=self.lobby_id)
        lobby.datetime_start_game = datetime.now()
        lobby.status = "Game started"
        lobby.save()

        self.dota.launch_practice_lobby()

    def controller_user_in_ui(self, message):
        if message.HasField('state') and message.state != 0:
            return

        logging.info("Game mode: %s vs_bots: %s", self.lobby_game_mode, self.vs_bots)

        if self.vs_bots:
            bot_steam_id = str(self.client.steam_id.as_64)
            good_count = sum(
                1 for m in message.all_members
                if m.team == DOTA_GC_TEAM.GOOD_GUYS
                and str(m.id) != bot_steam_id
            )
            logging.info("vs_bots slot check: good_count=%s bot_steam_id=%s", good_count, bot_steam_id)
            if self.lobby_game_mode in ("All Pick", "Captains Mode") and good_count == 5:
                self.launch_lobby()
            elif self.lobby_game_mode == "1v1 Solo Mid" and good_count == 1:
                self.launch_lobby()
        else:
            good_side, bad_side, position_is_set = check_slots(message, 0, 0, 0)
            if self.lobby_game_mode in ("All Pick", "Captains Mode") and good_side == 5 and bad_side == 5 and position_is_set == 10:
                self.launch_lobby()
            elif self.lobby_game_mode == "1v1 Solo Mid" and good_side == 1 and bad_side == 1 and position_is_set == 2:
                self.launch_lobby()

    def post_game_handler(self, message):
        try:
            logging.info(f"post_game message: {message}")

            result = self.get_result_from_match_outcome(message.match_outcome)
            queryset = []
            lobby = Lobby.objects.filter(id=self.lobby_id).first()

            for member in message.all_members[1:]:
                queryset, user_info_from_dota = parse_and_save_steam_massage(member, queryset)
                steam_id, team = user_info_from_dota

                if team in ["DOTA_GC_TEAM_GOOD_GUYS", "DOTA_GC_TEAM_BAD_GUYS"]:
                    user = CustomUser.objects.filter(steam_id=str(steam_id)).first()
                    if not user:
                        logging.warning("No user found for steam_id %s — skipping fund distribution", steam_id)
                        continue

                    if not check_if_lobby_blocked(lobby):
                        distribute_funds_and_mmr(user, lobby, team, result)

                    user.dota_game_history.add(self.game_history.id)
                    user.save()

            self.game_history.result = result
            self.game_history.players_info.set(queryset)
            self.game_history.save()

            lobby.status = "Finished"
            lobby.datetime_finish_game = timezone.now()
            lobby.game_history = self.game_history
            lobby.match_id = message.match_id
            lobby.save()

            if lobby.is_block:
                fill_data_about_blocked_users(lobby)
                send_block_info_to_bitrix(lobby)

            # Clean up memberships only after all funds have been distributed
            Membership.objects.filter(lobby__id=self.lobby_id).delete()
            self._finalize_lobby('Finished', 'game_complete')

        except Exception:
            logging.exception("Exception in post_game_handler for lobby %s", self.lobby_id)
            self._finalize_lobby('Error', 'post_game_exception')
        finally:
            logging.info("Match over — shutting down bot")
            self.shutdown_bot()

    @staticmethod
    def get_result_from_match_outcome(match_outcome):
        if match_outcome == 2:
            return "DOTA_GC_TEAM_GOOD_GUYS"
        elif match_outcome == 3:
            return "DOTA_GC_TEAM_BAD_GUYS"
        else:
            return "Unknown"

    # ── Shutdown ───────────────────────────────────────────────────────────────

    def _finalize_lobby(self, status: str, reason: str):
        """Set terminal lobby status and emit a structured log entry."""
        try:
            Lobby.objects.filter(id=self.lobby_id).update(status=status)
        except Exception:
            logging.exception("Failed to finalize lobby %s", self.lobby_id)
        logging.info(
            "LOBBY_FINALIZED lobby_id=%s status=%s reason=%s",
            self.lobby_id, status, reason,
        )

    def shutdown_bot(self):
        if getattr(self, '_shutdown_called', False):
            return
        self._shutdown_called = True

        self._cancel_timeout()
        self.dota.remove_all_listeners()
        self.client.remove_all_listeners()

        # abandon must come before exit
        try:
            self.dota.abandon_current_game()
        except Exception:
            pass
        try:
            self.dota.destroy_lobby()
        except Exception:
            pass
        try:
            self.dota.exit()
        except Exception:
            pass
        try:
            self.client.logout()
        except Exception:
            pass
        try:
            self.client.disconnect()
        except Exception:
            pass

        change_bot_status(self.bot_name, False)
        logging.info("Bot %s shut down.", self.bot_name)

        try:
            lobby = Lobby.objects.filter(id=self.lobby_id).first()
            if lobby and lobby.task_id:
                app.control.revoke(lobby.task_id, terminate=True)
        except Exception:
            logging.exception("Failed to revoke celery task")
