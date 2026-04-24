from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='authentication.CustomUser')
def create_wallet_for_new_user(sender, instance, created, **kwargs):
    if not created:
        return
    from payments.monetix.models import UserWallet
    UserWallet.objects.get_or_create(
        user=instance,
        defaults={'balance': 10000, 'currency': 'KZT'},
    )
