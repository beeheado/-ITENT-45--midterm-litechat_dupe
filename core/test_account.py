import re
from datetime import datetime, timezone

import pytest
from django.urls import reverse

from core import ledger
from core.models import Wallet

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(django_user_model):
    u = django_user_model.objects.create_user("ann", password="pw", first_name="Ann", last_name="Lee")
    u.date_joined = datetime(2026, 3, 5, 12, 0, tzinfo=timezone.utc)
    u.save()
    return u


@pytest.fixture
def logged(client, user):
    client.force_login(user)
    client.user = user
    return client


def page(client):
    return client.get(reverse("account")).content.decode()


def test_login_required(client):
    r = client.get(reverse("account"))
    assert r.status_code == 302 and "/login/" in r["Location"]


def test_profile_card_shows_the_four_fields(logged, user):
    html = page(logged)
    for label in ("Display Name", "Username", "User ID", "Member Since"):
        assert label in html
    assert ">Ann Lee<" in html and ">ann<" in html and f"<dd>{user.pk}</dd>" in html
    assert "March 05, 2026" in html  # Month DD, YYYY


def test_display_name_falls_back_to_username(client, django_user_model):
    u = django_user_model.objects.create_user("plain", password="pw")
    client.force_login(u)
    html = page(client)
    assert "[Personal] plain" in html and "<dd>plain</dd>" in html


def test_billing_card_label_badge_and_currency_format(logged, user):
    ledger.credit(Wallet.objects.get(user=user).pk, 1_000_000, "topup")  # $1 welcome + $1 = $2.00
    html = page(logged)
    assert "[Personal] Ann Lee" in html and "ACTIVE" in html and "INACTIVE" not in html
    assert "AVAILABLE CREDIT" in html and "$2.00" in html


def test_inactive_user_shows_inactive_badge(client, django_user_model):
    u = django_user_model.objects.create_user("gone", password="pw")
    client.force_login(u)
    u.is_active = False
    u.save()
    # An inactive user cannot stay logged in, so check the template logic through the context instead.
    from django.template.loader import render_to_string

    html = render_to_string("account.html", {"user": u, "display_name": "gone", "balance_micros": 0, "profile": None})
    assert "INACTIVE" in html


def test_back_to_app_link_and_header_link(logged):
    html = page(logged)
    assert re.search(r'<p class="back"><a href="/">Back to App</a></p>', html)
    assert 'href="/account/"' in html  # header link


def test_signup_collects_an_optional_display_name(client):
    r = client.post(reverse("signup"), {"username": "newbie", "first_name": "Nia Novak",
                                        "password1": "s3cret-Pass!9", "password2": "s3cret-Pass!9"})
    assert r.status_code == 302
    assert "[Personal] Nia Novak" in page(client)


def test_signup_still_works_without_a_display_name(client):
    r = client.post(reverse("signup"), {"username": "quiet", "password1": "s3cret-Pass!9", "password2": "s3cret-Pass!9"})
    assert r.status_code == 302 and "[Personal] quiet" in page(client)


# --- global system prompt ---
from core import views  # noqa: E402
from core.models import Conversation, LLMModel, MAX_PROMPT_CHARS, UserProfile  # noqa: E402
from core.providers.types import Done, TextDelta, Usage  # noqa: E402


class FakeAdapter:
    def __init__(self):
        self.requests = []

    def stream(self, req):
        self.requests.append(req)
        yield TextDelta("ok")
        yield Usage(10, 2)
        yield Done("stop")


def save_prompt(client, text):
    return client.post(reverse("save_prompt"), {"system_prompt": text}, follow=True)


def test_prompt_section_has_the_exact_spec_text(logged):
    html = page(logged)
    assert 'placeholder="e.g., You are a helpful assistant that..."' in html
    assert "This instruction will apply to all chat sessions." in html
    assert ">Save Prompt<" in html and "<textarea" in html


def test_saving_the_prompt_persists_shows_it_and_flashes(logged, user):
    r = save_prompt(logged, "Answer like a pirate.\nBe brief.")
    html = r.content.decode()
    assert "System prompt saved." in html  # flash message rendered once, after the redirect
    assert UserProfile.objects.get(user=user).system_prompt == "Answer like a pirate.\nBe brief."
    assert "Answer like a pirate." in html  # and the textarea is pre-filled
    assert "System prompt saved." not in page(logged)  # flash is shown once only


def test_prompt_can_be_cleared(logged, user):
    save_prompt(logged, "x")
    save_prompt(logged, "")
    assert UserProfile.objects.get(user=user).system_prompt == ""


def test_too_long_prompt_is_rejected_and_not_saved(logged, user):
    save_prompt(logged, "keep me")
    r = save_prompt(logged, "y" * (MAX_PROMPT_CHARS + 1))
    assert "too long" in r.content.decode()
    assert UserProfile.objects.get(user=user).system_prompt == "keep me"


def test_prompt_is_escaped_on_the_page(logged):
    html = save_prompt(logged, "</textarea><script>alert(1)</script>").content.decode()
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_prompt_actions_require_login_and_post(client, logged):
    assert logged.get(reverse("save_prompt")).status_code == 405
    client.logout()
    r = client.post(reverse("save_prompt"), {"system_prompt": "x"})
    assert r.status_code == 302 and "/login/" in r["Location"]


def test_prompt_is_sent_to_the_model_and_edits_apply_to_existing_chats(logged, user, monkeypatch):
    fake = FakeAdapter()
    monkeypatch.setattr(views, "get_adapter", lambda provider: fake)
    model = LLMModel.objects.get(provider="anthropic")
    conv = Conversation.objects.create(user=user, model=model)

    def send(text):
        r = logged.post(reverse("send", args=[conv.pk]), {"content": text, "model": model.pk})
        b"".join(r.streaming_content)

    send("first")  # no prompt yet
    save_prompt(logged, "Always speak French.")
    send("second")  # same conversation, new prompt applies immediately
    save_prompt(logged, "")
    send("third")
    assert [r.system for r in fake.requests] == ["", "Always speak French.", ""]


def test_system_text_is_counted_in_the_reserve_estimate():
    from core import ledger
    from core.providers.types import ChatMessage

    model = LLMModel.objects.get(provider="anthropic")
    msgs = [ChatMessage("user", "hi")]
    assert ledger.estimate_reserve(model, msgs, "x" * 3000) > ledger.estimate_reserve(model, msgs)
