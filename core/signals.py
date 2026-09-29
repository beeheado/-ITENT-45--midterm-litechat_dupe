from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from . import ledger
from .models import Wallet


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallet_with_grant(sender, instance, created, **kwargs):
    if created:
        wallet = Wallet.objects.create(user=instance)
        if settings.STARTING_GRANT_MICROS:
            ledger.credit(wallet.pk, settings.STARTING_GRANT_MICROS, "grant", note="Welcome credit")
