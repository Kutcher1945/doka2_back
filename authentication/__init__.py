from django.db.models import TextChoices

class UserOnlineStatuses(TextChoices):
    ONLINE = 'ONLINE', 'В сети'
    OFFLINE = 'OFFLINE', 'Не в сети'
