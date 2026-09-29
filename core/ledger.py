"""Money movement. All balance changes go through here so ledger and wallet never drift."""
from django.db import transaction

from .models import LedgerEntry, Wallet


class InsufficientBalance(Exception):
    pass


@transaction.atomic
def credit(wallet_id, amount_micros, kind, note="", message=None):
    """Apply a signed amount to a wallet and append the matching ledger row, atomically."""
    wallet = Wallet.objects.select_for_update().get(pk=wallet_id)
    new_balance = wallet.balance_micros + amount_micros
    if new_balance < 0:
        raise InsufficientBalance(f"balance {wallet.balance_micros} cannot cover {amount_micros}")
    wallet.balance_micros = new_balance
    wallet.save(update_fields=["balance_micros"])
    return LedgerEntry.objects.create(
        wallet=wallet, kind=kind, amount_micros=amount_micros,
        balance_after_micros=new_balance, note=note, message=message,
    )
