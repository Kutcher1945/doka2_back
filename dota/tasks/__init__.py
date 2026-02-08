from core.celery import app
from dota.task import ControllerDota

controller_dota_task = app.register_task(ControllerDota)
