from django.db.models import TextChoices


class FriendshipStatuses(TextChoices):
    REQUESTED = 'REQUESTED', 'Запрос в обработке'
    APPROVED = 'APPROVED', 'Принято'
    REJECTED = 'REJECTED', 'Отклонено'
    DELETED = 'DELETED', 'Удален'
