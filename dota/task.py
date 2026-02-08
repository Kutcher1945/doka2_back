from celery import Task

from dota import controller_dota2


class ControllerDota(Task):
    def run(self, lobby_id, lobby_name, lobby_password, q_lobby_players, lobby_game_mode, bot_name, bot_password):
        print('START TASK')
        dota_lobby_manager = controller_dota2.DotaLobbyManager(lobby_id, lobby_name, lobby_password,
                                                                q_lobby_players,
                                                                lobby_game_mode, bot_name, bot_password)
        print("STEP 1")
        dota_lobby_manager.main()
