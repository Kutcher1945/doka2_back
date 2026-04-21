from celery import Task

from dota import controller_dota2


class ControllerDota(Task):
    def run(self, lobby_id, lobby_name, lobby_password, q_lobby_players, lobby_game_mode, bot_name, bot_password, vs_bots=False):
        from dota.utils import change_bot_status
        from dota.models import Lobby
        print('START TASK')
        try:
            dota_lobby_manager = controller_dota2.DotaLobbyManager(
                lobby_id, lobby_name, lobby_password, q_lobby_players,
                lobby_game_mode, bot_name, bot_password, vs_bots,
            )
            print("STEP 1")
            dota_lobby_manager.main()
        except Exception as e:
            print(f'TASK ERROR: {e}')
            change_bot_status(bot_name, False)
            lobby = Lobby.objects.filter(id=lobby_id).first()
            if lobby and lobby.status not in ('Finished', 'Error'):
                lobby.status = 'Error'
                lobby.save(update_fields=['status'])
            raise
