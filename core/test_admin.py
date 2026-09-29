import pytest
from django.contrib.admin.sites import site
from django.urls import reverse

from core.models import LedgerEntry, Wallet
from core.test_ledger import assert_ledger_consistent

pytestmark = pytest.mark.django_db


@pytest.fixture
def superuser(django_user_model):
    return django_user_model.objects.create_superuser("root", "r@example.com", "pw")


@pytest.fixture
def wallet(django_user_model):
    return Wallet.objects.get(user=django_user_model.objects.create_user("ann", password="pw"))


def run_action(client, name, wallet):
    return client.post(
        reverse("admin:core_wallet_changelist"),
        {"action": name, "_selected_action": [wallet.pk]},
        follow=True,
    )


def test_grant_actions_are_registered():
    actions = site._registry[Wallet].actions
    assert [a.__name__ for a in actions] == ["grant_1", "grant_5", "grant_10"]


def test_grant_credits_wallet_through_ledger(client, superuser, wallet):
    client.force_login(superuser)
    r = run_action(client, "grant_5", wallet)
    assert r.status_code == 200 and "Granted $5" in r.content.decode()
    wallet.refresh_from_db()
    assert wallet.balance_micros == 6_000_000  # $1 welcome + $5
    entry = LedgerEntry.objects.filter(wallet=wallet, kind="topup").get()
    assert entry.amount_micros == 5_000_000 and "root" in entry.note
    assert_ledger_consistent(wallet)


def test_regular_user_cannot_grant(client, django_user_model, wallet):
    client.force_login(django_user_model.objects.create_user("bob", password="pw"))
    run_action(client, "grant_10", wallet)
    wallet.refresh_from_db()
    assert wallet.balance_micros == 1_000_000 and not LedgerEntry.objects.filter(kind="topup").exists()


def test_wallet_balance_is_not_editable_in_admin(client, superuser, wallet):
    client.force_login(superuser)
    page = client.get(reverse("admin:core_wallet_change", args=[wallet.pk])).content.decode()
    assert 'name="balance_micros"' not in page
