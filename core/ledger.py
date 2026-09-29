"""Money movement and metering. All balance changes go through here so ledger and wallet never drift.

Units: micro-credits (1 credit = $1). Prices are micro-credits per million tokens.
"""
from django.db import transaction

from .models import NO_ANSWER, NO_ANSWER_TRUNCATED, LedgerEntry, Wallet
from .providers.types import is_truncated

MTOK = 1_000_000
CHARS_PER_TOKEN = 3  # deliberately pessimistic; only used for the pre-flight reserve, never for billing
# The reserve assumes at most this many output tokens, so a user with a few cents left can still ask a short question.
# A reply that runs longer can overshoot the balance slightly; credit(..., clamp=True) then stops it at zero.
RESERVE_OUTPUT_TOKENS = 2048


class InsufficientBalance(Exception):
    pass


def cost_for(model, input_tokens, output_tokens):
    """Cost in micro-credits, rounded up so we never undercharge by a fraction."""
    total = input_tokens * model.input_price_micros_per_mtok + output_tokens * model.output_price_micros_per_mtok
    return -(-total // MTOK)


def estimate_reserve(model, messages):
    """Upper-bound-ish cost of a request, used to refuse it up front if the balance can't cover it."""
    est_input = sum(len(m.content) for m in messages) // CHARS_PER_TOKEN + 1
    return cost_for(model, est_input, min(model.max_output_tokens, RESERVE_OUTPUT_TOKENS))


def ensure_can_afford(wallet, reserve_micros):
    wallet.refresh_from_db()
    if wallet.balance_micros < reserve_micros:
        raise InsufficientBalance(f"need {reserve_micros}, have {wallet.balance_micros}")


@transaction.atomic
def credit(wallet_id, amount_micros, kind, note="", message=None, clamp=False):
    """Apply a signed amount to a wallet and append the matching ledger row, atomically.

    With clamp=True a debit larger than the balance is reduced to the balance (never below zero);
    otherwise it raises InsufficientBalance.
    """
    wallet = Wallet.objects.select_for_update().get(pk=wallet_id)
    if amount_micros < 0 and wallet.balance_micros + amount_micros < 0:
        if not clamp:
            raise InsufficientBalance(f"balance {wallet.balance_micros} cannot cover {-amount_micros}")
        note = f"{note} (clamped from {-amount_micros})".strip()
        amount_micros = -wallet.balance_micros
    wallet.balance_micros += amount_micros
    wallet.save(update_fields=["balance_micros"])
    return LedgerEntry.objects.create(
        wallet=wallet, kind=kind, amount_micros=amount_micros,
        balance_after_micros=wallet.balance_micros, note=note, message=message,
    )


@transaction.atomic
def finalize_message(message, *, content, reasoning="", usage=None, status="complete", error="", finish_reason=""):
    """Finish an assistant message and bill it in ONE transaction: both happen or neither does.

    Policy: bill only from usage the provider reported, and only when the user got something visible.
      - no usage (failure, dropped stream): saved, not charged
      - no visible answer (e.g. the model spent its whole budget on reasoning): failed, not charged
      - partial or complete answer: charged for the reported tokens
    """
    visible = bool(content.strip())
    cost = 0
    if usage is not None:
        message.input_tokens, message.output_tokens = usage.input_tokens, usage.output_tokens
        if visible:
            cost = cost_for(message.model, usage.input_tokens, usage.output_tokens)
    if status == "complete":
        if usage is None:
            status, error = "failed", error or "Provider reported no usage; not charged."
        elif not visible:
            status = "failed"
            error = error or (NO_ANSWER_TRUNCATED if is_truncated(finish_reason) else NO_ANSWER)
    message.content, message.reasoning, message.finish_reason = content, reasoning, finish_reason
    message.status, message.error, message.cost_micros = status, error, cost
    message.save()
    if cost:
        wallet_id = message.conversation.user.wallet.pk
        credit(wallet_id, -cost, "charge", note=message.model.display_name, message=message, clamp=True)
    return message
