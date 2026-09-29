import pytest
from django.db.models import Sum

from core import ledger
from core.models import Conversation, LedgerEntry, LLMModel, Message, Wallet
from core.providers.types import ChatMessage, Usage

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user("ann", password="x")  # starts with the $1 grant


@pytest.fixture
def wallet(user):
    return Wallet.objects.get(user=user)


@pytest.fixture
def model():
    return LLMModel.objects.get(model_id="claude-haiku-4-5-20251001")  # $1 in / $5 out per Mtok


@pytest.fixture
def pending(user, model):
    conv = Conversation.objects.create(user=user, model=model)
    return Message.objects.create(conversation=conv, role="assistant", model=model, status="pending")


def assert_ledger_consistent(wallet):
    wallet.refresh_from_db()
    assert wallet.entries.aggregate(s=Sum("amount_micros"))["s"] == wallet.balance_micros
    last = wallet.entries.order_by("id").last()
    assert last.balance_after_micros == wallet.balance_micros
    assert wallet.balance_micros >= 0


def test_cost_for_integer_math_rounds_up(model):
    assert ledger.cost_for(model, 1_000_000, 0) == 1_000_000
    assert ledger.cost_for(model, 0, 1_000_000) == 5_000_000
    assert ledger.cost_for(model, 208, 17) == 293  # 208*1 + 17*5 = 293 micros exactly
    assert ledger.cost_for(model, 1, 0) == 1  # a fraction of a micro rounds up to 1
    assert ledger.cost_for(model, 0, 0) == 0


def test_credit_and_debit_keep_ledger_consistent(wallet):
    ledger.credit(wallet.pk, 500_000, "adjustment", note="bonus")
    ledger.credit(wallet.pk, -200_000, "charge")
    assert_ledger_consistent(wallet)
    assert wallet.balance_micros == 1_300_000


def test_debit_beyond_balance_raises_and_changes_nothing(wallet):
    with pytest.raises(ledger.InsufficientBalance):
        ledger.credit(wallet.pk, -5_000_000, "charge")
    assert_ledger_consistent(wallet)
    assert wallet.balance_micros == 1_000_000 and wallet.entries.count() == 1


def test_clamped_debit_stops_at_zero_and_notes_it(wallet):
    entry = ledger.credit(wallet.pk, -5_000_000, "charge", clamp=True)
    assert entry.amount_micros == -1_000_000 and "clamped" in entry.note
    assert_ledger_consistent(wallet)
    assert wallet.balance_micros == 0


def test_finalize_bills_from_reported_usage(wallet, pending):
    ledger.finalize_message(pending, content="pong", reasoning="hm", usage=Usage(208, 17))
    pending.refresh_from_db()
    assert (pending.status, pending.cost_micros, pending.input_tokens, pending.output_tokens) == ("complete", 293, 208, 17)
    assert pending.reasoning == "hm"
    entry = LedgerEntry.objects.get(message=pending)
    assert entry.kind == "charge" and entry.amount_micros == -293
    assert_ledger_consistent(wallet)


def test_price_change_does_not_rewrite_history(wallet, pending, model):
    ledger.finalize_message(pending, content="x", usage=Usage(1000, 1000))
    before = Message.objects.get(pk=pending.pk).cost_micros
    model.output_price_micros_per_mtok *= 10
    model.save()
    assert Message.objects.get(pk=pending.pk).cost_micros == before


def test_no_usage_means_failed_and_free(wallet, pending):
    ledger.finalize_message(pending, content="partial", usage=None)
    pending.refresh_from_db()
    assert pending.status == "failed" and pending.cost_micros == 0 and pending.error
    assert wallet.entries.count() == 1  # only the welcome grant
    assert_ledger_consistent(wallet)


def test_failed_with_usage_is_still_billed(wallet, pending):
    ledger.finalize_message(pending, content="part", usage=Usage(100, 10), status="cancelled", error="client left")
    pending.refresh_from_db()
    assert pending.status == "cancelled" and pending.cost_micros > 0
    assert_ledger_consistent(wallet)


def test_charge_and_message_roll_back_together(wallet, pending, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(LedgerEntry.objects, "create", boom)
    with pytest.raises(RuntimeError):
        ledger.finalize_message(pending, content="pong", usage=Usage(208, 17))
    pending.refresh_from_db()
    assert pending.status == "pending" and pending.cost_micros == 0 and pending.content == ""
    assert_ledger_consistent(wallet)
    assert wallet.balance_micros == 1_000_000


def test_overdraft_is_clamped_not_negative(wallet, pending):
    ledger.credit(wallet.pk, -999_990, "adjustment")  # leave 10 micro-credits
    ledger.finalize_message(pending, content="big", usage=Usage(1_000_000, 1_000_000))
    pending.refresh_from_db()
    assert pending.cost_micros == 6_000_000  # true cost recorded on the message
    assert_ledger_consistent(wallet)
    assert wallet.balance_micros == 0


def test_reserve_and_affordability(wallet, model):
    msgs = [ChatMessage("user", "x" * 300)]
    reserve = ledger.estimate_reserve(model, msgs)
    assert model.max_output_tokens > ledger.RESERVE_OUTPUT_TOKENS  # the cap is what keeps the reserve small
    assert reserve == ledger.cost_for(model, 101, ledger.RESERVE_OUTPUT_TOKENS)
    ledger.ensure_can_afford(wallet, reserve)  # $1 covers it
    ledger.credit(wallet.pk, -999_999, "adjustment")
    with pytest.raises(ledger.InsufficientBalance):
        ledger.ensure_can_afford(wallet, reserve)


# --- no visible answer / truncation policy ---
from core.models import CUT_OFF, NO_ANSWER, NO_ANSWER_TRUNCATED  # noqa: E402


def test_truncated_with_no_answer_is_free_and_failed(wallet, pending):
    ledger.finalize_message(pending, content="", reasoning="thinking...", usage=Usage(211, 8192), finish_reason="length")
    pending.refresh_from_db()
    assert pending.status == "failed" and pending.cost_micros == 0
    assert pending.error == NO_ANSWER_TRUNCATED and pending.notice == NO_ANSWER_TRUNCATED
    assert (pending.input_tokens, pending.output_tokens, pending.finish_reason) == (211, 8192, "length")  # tokens still recorded
    assert pending.reasoning == "thinking..."
    assert wallet.entries.count() == 1  # only the welcome grant: nothing charged
    assert_ledger_consistent(wallet)


def test_empty_reply_that_was_not_truncated_gets_generic_notice(wallet, pending):
    ledger.finalize_message(pending, content="   ", usage=Usage(10, 1), finish_reason="stop")
    pending.refresh_from_db()
    assert pending.status == "failed" and pending.cost_micros == 0 and pending.error == NO_ANSWER


def test_partial_answer_cut_off_is_still_billed_with_a_note(wallet, pending):
    ledger.finalize_message(pending, content="The first half of", usage=Usage(200, 8000), finish_reason="max_tokens")
    pending.refresh_from_db()
    assert pending.status == "complete" and pending.cost_micros > 0 and pending.truncated
    assert pending.notice == CUT_OFF and not pending.error
    assert LedgerEntry.objects.filter(message=pending, kind="charge").count() == 1
    assert_ledger_consistent(wallet)


def test_provider_error_with_usage_but_no_text_is_free(wallet, pending):
    ledger.finalize_message(pending, content="", usage=Usage(100, 5), status="failed", error="boom")
    pending.refresh_from_db()
    assert pending.cost_micros == 0 and pending.error == "boom"
    assert wallet.entries.count() == 1


def test_notice_covers_old_rows_saved_before_finish_reason_existed(pending):
    pending.status, pending.content, pending.finish_reason, pending.error = "complete", "", "", ""
    assert pending.notice == NO_ANSWER  # e.g. the blank replies created before the fix
    pending.content = "fine"
    assert pending.notice == ""


def test_seeded_models_have_a_budget_big_enough_to_finish_thinking():
    assert set(LLMModel.objects.values_list("max_output_tokens", flat=True)) == {8192}
    assert LLMModel._meta.get_field("max_output_tokens").default == 8192
