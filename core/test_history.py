import pytest
from django.urls import reverse

from core import ledger
from core.models import Conversation, LLMModel, Message, Wallet
from core.providers.types import Usage

pytestmark = pytest.mark.django_db


@pytest.fixture
def model():
    return LLMModel.objects.get(model_id="gpt-5.6-luna")


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user("ann", password="pw")


@pytest.fixture
def logged(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def conv(user, model):
    return Conversation.objects.create(user=user, model=model, title="Old title")


def test_rename(logged, conv):
    assert logged.post(reverse("rename", args=[conv.pk]), {"title": "  Trip plans  "}).status_code == 302
    conv.refresh_from_db()
    assert conv.title == "Trip plans"


def test_blank_rename_is_ignored(logged, conv):
    logged.post(reverse("rename", args=[conv.pk]), {"title": "   "})
    conv.refresh_from_db()
    assert conv.title == "Old title"


def test_delete_removes_messages_but_keeps_ledger(logged, conv, model, user):
    reply = Message.objects.create(conversation=conv, role="assistant", model=model, status="pending")
    ledger.finalize_message(reply, content="x", usage=Usage(100, 100))
    balance = Wallet.objects.get(user=user).balance_micros
    assert logged.post(reverse("delete", args=[conv.pk])).status_code == 302
    assert not Conversation.objects.filter(pk=conv.pk).exists() and not Message.objects.exists()
    assert Wallet.objects.get(user=user).balance_micros == balance
    assert "Charge" in logged.get(reverse("usage")).content.decode()  # the money trail survives


def test_history_actions_are_post_only(logged, conv):
    assert logged.get(reverse("delete", args=[conv.pk])).status_code == 405
    assert logged.get(reverse("rename", args=[conv.pk])).status_code == 405


def test_users_cannot_touch_each_others_chats(client, django_user_model, conv):
    client.force_login(django_user_model.objects.create_user("eve", password="pw"))
    assert client.post(reverse("rename", args=[conv.pk]), {"title": "pwned"}).status_code == 404
    assert client.post(reverse("delete", args=[conv.pk])).status_code == 404
    conv.refresh_from_db()
    assert conv.title == "Old title"


def test_sidebar_only_lists_own_chats(client, django_user_model, conv):
    eve = django_user_model.objects.create_user("eve", password="pw")
    client.force_login(eve)
    assert "Old title" not in client.get(reverse("chat_home")).content.decode()


def test_usage_page_totals_and_isolation(logged, conv, model, user, django_user_model):
    reply = Message.objects.create(conversation=conv, role="assistant", model=model, status="pending")
    ledger.finalize_message(reply, content="x", usage=Usage(1_000_000, 0))  # $0.25 at the seeded price
    page = logged.get(reverse("usage")).content.decode()
    assert "Welcome credit" in page and "Old title" in page and "0.250000" in page
    logged.logout()
    other = django_user_model.objects.create_user("bo", password="pw")
    logged.force_login(other)
    assert "Old title" not in logged.get(reverse("usage")).content.decode()


def test_usage_requires_login(client):
    assert client.get(reverse("usage")).status_code == 302
