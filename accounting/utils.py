import logging

from authentication.models import CustomUser
from django.utils import timezone
from dota.models import Lobby

from .models import Accounting, AccountingHistory

logger = logging.getLogger(__name__)


def save_accounting_data(lobby: Lobby, user: CustomUser, amount: float) -> None:
    """
    Save accounting data, update summary balance, and create history for accounting.

    Args:
        lobby (Lobby): The lobby for the accounting.
        user (CustomUser): The user associated with the accounting.
        amount (float): The amount to be added to balance.
    """

    accounting, created = Accounting.objects.get_or_create(pk=1)
    accounting.balance += amount
    accounting.save()

    AccountingHistory.objects.create(accounting=accounting,
                                     lobby=lobby,
                                     datetime=timezone.now(),
                                     service_earning=amount,
                                     user=user)
