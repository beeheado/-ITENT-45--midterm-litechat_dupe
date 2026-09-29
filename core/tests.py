import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_signup_logs_user_in(client):
    r = client.post(reverse("signup"), {"username": "ann", "password1": "s3cret-Pass!9", "password2": "s3cret-Pass!9"})
    assert r.status_code == 302
    assert client.get(reverse("chat_home")).status_code == 200


@pytest.mark.django_db
def test_login_required(client):
    r = client.get(reverse("chat_home"))
    assert r.status_code == 302 and "/login/" in r["Location"]


@pytest.mark.django_db
def test_login_and_logout(client, django_user_model):
    django_user_model.objects.create_user("bob", password="pw-12345-xyz")
    assert client.post(reverse("login"), {"username": "bob", "password": "pw-12345-xyz"}).status_code == 302
    assert client.post(reverse("logout")).status_code == 302
    assert client.get(reverse("chat_home")).status_code == 302


# --- models ---
from django.db import IntegrityError, transaction  # noqa: E402

from core.models import LedgerEntry, LLMModel, Wallet  # noqa: E402


@pytest.mark.django_db
def test_seed_models_present():
    assert set(LLMModel.objects.values_list("provider", flat=True)) == {"openai", "anthropic", "google"}


@pytest.mark.django_db
def test_new_user_gets_wallet_and_grant(django_user_model, settings):
    u = django_user_model.objects.create_user("cy", password="x")
    wallet = Wallet.objects.get(user=u)  # reload: the signal updated it after u.wallet was cached
    assert wallet.balance_micros == settings.STARTING_GRANT_MICROS
    e = LedgerEntry.objects.get(wallet=wallet)
    assert (e.kind, e.balance_after_micros) == ("grant", settings.STARTING_GRANT_MICROS)


@pytest.mark.django_db
def test_wallet_balance_cannot_go_negative(django_user_model):
    w = django_user_model.objects.create_user("di", password="x").wallet
    with pytest.raises(IntegrityError), transaction.atomic():
        Wallet.objects.filter(pk=w.pk).update(balance_micros=-1)
