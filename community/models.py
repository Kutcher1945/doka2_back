from django.db import models
from django.utils import timezone

from community import FriendshipStatuses


class Friendship(models.Model):
    status = models.CharField("Статус",
                              choices=FriendshipStatuses.choices,
                              default=FriendshipStatuses.REQUESTED,
                              max_length=255)
    requested_user = models.ForeignKey(
        "authentication.CustomUser",
        verbose_name='Отправитель',
        on_delete=models.CASCADE,
        related_name='sent_friends'
    )
    addressee_user = models.ForeignKey(
        "authentication.CustomUser",
        verbose_name='Получатель',
        on_delete=models.CASCADE,
        related_name='receive_friends'
    )
    datetime_create = models.DateTimeField(default=timezone.now,
                                           verbose_name='Дата создания')
    datetime_approve = models.DateTimeField(null=True,
                                            verbose_name='Дата добавления')
