import pusher
from django.conf import settings

_pusher_client = None


def get_pusher_client():
    global _pusher_client
    if _pusher_client is None:
        _pusher_client = pusher.Pusher(
            app_id=settings.PUSHER_APP_ID,
            key=settings.PUSHER_KEY,
            secret=settings.PUSHER_SECRET,
            cluster=settings.PUSHER_CLUSTER,
            ssl=True,
        )
    return _pusher_client


pusher_client = None
