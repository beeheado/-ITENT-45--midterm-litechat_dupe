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


# --- memory items ---
from core.models import MAX_MEMORY_CHARS, MAX_MEMORY_ITEMS, MemoryItem  # noqa: E402
from core.prompting import build_system_prompt  # noqa: E402


def add(client, kind="preference", content="I like short answers"):
    return client.post(reverse("add_memory"), {"kind": kind, "content": content}, follow=True)


def test_memory_section_has_the_exact_spec_text_and_empty_state(logged):
    html = page(logged)
    assert "Generate AI Memories" in html
    assert 'Allow the application to crawl your previous conversations with AI to generate AI-managed "memories" that will help personalize your experience.' in html
    assert "No memory items yet. Add your first one above." in html
    assert 'placeholder="Enter memory content..."' in html and ">Add Memory Item<" in html
    for label in ("Preference", "Fact"):
        assert f">{label}</option>" in html


def test_empty_state_appears_above_which_the_add_form_sits(logged):
    html = page(logged)
    assert html.index("Add Memory Item") < html.index("No memory items yet")  # "add your first one above" is true


def test_add_lists_and_flashes(logged, user):
    html = add(logged, "fact", "I live in Lisbon").content.decode()
    assert "Memory added." in html and "I live in Lisbon" in html and ">Fact<" in html
    assert "No memory items yet" not in html
    assert MemoryItem.objects.get(user=user).kind == "fact"


def test_blank_or_invalid_memory_is_rejected(logged, user):
    assert "Enter some text" in add(logged, "fact", "   ").content.decode()
    assert "Enter some text" in add(logged, "bogus", "x").content.decode()
    assert "Enter some text" in add(logged, "fact", "z" * (MAX_MEMORY_CHARS + 1)).content.decode()
    assert not MemoryItem.objects.exists()


def test_memory_cap(logged, user):
    MemoryItem.objects.bulk_create(MemoryItem(user=user, content=f"m{i}") for i in range(MAX_MEMORY_ITEMS))
    assert f"up to {MAX_MEMORY_ITEMS}" in add(logged).content.decode()
    assert MemoryItem.objects.filter(user=user).count() == MAX_MEMORY_ITEMS


def test_delete_own_memory(logged, user):
    m = MemoryItem.objects.create(user=user, content="bye")
    r = logged.post(reverse("delete_memory", args=[m.pk]), follow=True)
    assert "Memory deleted." in r.content.decode() and not MemoryItem.objects.exists()


def test_cannot_delete_someone_elses_memory(logged, django_user_model):
    other = django_user_model.objects.create_user("eve", password="pw")
    m = MemoryItem.objects.create(user=other, content="private")
    assert logged.post(reverse("delete_memory", args=[m.pk])).status_code == 404
    assert MemoryItem.objects.filter(pk=m.pk).exists()


def test_memories_are_private_to_their_owner(logged, django_user_model):
    other = django_user_model.objects.create_user("eve", password="pw")
    MemoryItem.objects.create(user=other, content="eve's secret")
    assert "eve's secret" not in page(logged)


def test_memory_text_is_escaped(logged):
    html = add(logged, "fact", "<img src=x onerror=alert(1)>").content.decode()
    assert "<img src=x" not in html and "&lt;img src=x" in html


def test_memory_actions_require_login_and_post(client, logged):
    assert logged.get(reverse("add_memory")).status_code == 405
    client.logout()
    assert client.post(reverse("add_memory"), {"kind": "fact", "content": "x"}).status_code == 302
    assert not MemoryItem.objects.exists()


def test_auto_memory_toggle_persists_both_ways(logged, user):
    logged.post(reverse("set_auto_memory"), {"auto_memory": "on"})
    assert UserProfile.objects.get(user=user).auto_memory is True
    assert "checked" in page(logged).split('name="auto_memory"')[1].split(">")[0]
    logged.post(reverse("set_auto_memory"), {})  # unchecked boxes send nothing
    assert UserProfile.objects.get(user=user).auto_memory is False


def test_memories_are_added_to_the_system_text(user):
    assert build_system_prompt(user) == ""
    MemoryItem.objects.create(user=user, kind="preference", content="I am vegetarian")
    MemoryItem.objects.create(user=user, kind="fact", content="I live in Lisbon")
    assert build_system_prompt(user) == (
        "Things to remember about the user:\n- [Preference] I am vegetarian\n- [Fact] I live in Lisbon"
    )
    p = UserProfile.objects.get(user=user)
    p.system_prompt = "Be brief."
    p.save()
    assert build_system_prompt(user).startswith("Be brief.\n\nThings to remember about the user:\n- [Preference]")


def test_memories_reach_the_model_through_send(logged, user, monkeypatch):
    fake = FakeAdapter()
    monkeypatch.setattr(views, "get_adapter", lambda provider: fake)
    model = LLMModel.objects.get(provider="anthropic")
    conv = Conversation.objects.create(user=user, model=model)
    add(logged, "preference", "I am vegetarian")
    b"".join(logged.post(reverse("send", args=[conv.pk]), {"content": "dinner?", "model": model.pk}).streaming_content)
    assert "[Preference] I am vegetarian" in fake.requests[0].system


def test_other_users_memories_never_leak_into_my_requests(user, django_user_model):
    other = django_user_model.objects.create_user("eve", password="pw")
    MemoryItem.objects.create(user=other, content="eve's secret")
    assert "eve's secret" not in build_system_prompt(user)


# --- default app + login redirect ---
from core.account_views import APP_HOME  # noqa: E402


def choose(client, value):
    return client.post(reverse("set_default_app"), {"default_app": value}, follow=True)


def checked_labels(html):
    return re.findall(r'aria-checked="true">([^<]+)<', html)


def test_default_app_section_text_and_three_choices(logged):
    html = page(logged)
    assert "Choose which app you land on after logging in." in html
    for label in ("SimGen", "Ask", "Chat"):
        assert f">{label}</button>" in html
    assert checked_labels(html) == ["Chat"]  # default highlighted


@pytest.mark.parametrize("value,label", [("simgen", "SimGen"), ("ask", "Ask"), ("chat", "Chat")])
def test_choosing_persists_and_highlights_only_that_option(logged, user, value, label):
    html = choose(logged, value).content.decode()
    assert UserProfile.objects.get(user=user).default_app == value
    assert checked_labels(html) == [label] and f"land on {label} after logging in" in html
    assert checked_labels(page(logged)) == [label]  # still selected on a fresh load


def test_invalid_default_app_is_rejected(logged, user):
    choose(logged, "simgen")
    assert "Pick SimGen, Ask or Chat." in choose(logged, "hacker").content.decode()
    assert UserProfile.objects.get(user=user).default_app == "simgen"


def test_default_app_actions_require_login_and_post(client, logged):
    assert logged.get(reverse("set_default_app")).status_code == 405
    client.logout()
    assert client.post(reverse("set_default_app"), {"default_app": "ask"}).status_code == 302


@pytest.mark.parametrize("choice", ["simgen", "ask", "chat"])
def test_login_lands_on_the_mapped_app(client, django_user_model, choice, monkeypatch):
    u = django_user_model.objects.create_user("lee", password="pw-12345-xyz")
    UserProfile.objects.filter(user=u).update(default_app=choice)
    r = client.post(reverse("login"), {"username": "lee", "password": "pw-12345-xyz"})
    assert r.status_code == 302 and r["Location"] == reverse(APP_HOME[choice])


def test_login_uses_the_mapping_so_a_future_app_is_one_line(client, django_user_model, monkeypatch):
    monkeypatch.setitem(APP_HOME, "ask", "usage")  # pretend Ask now has its own home
    u = django_user_model.objects.create_user("lee", password="pw-12345-xyz")
    UserProfile.objects.filter(user=u).update(default_app="ask")
    r = client.post(reverse("login"), {"username": "lee", "password": "pw-12345-xyz"})
    assert r["Location"] == reverse("usage")


def test_explicit_next_still_wins_over_the_default_app(client, django_user_model):
    django_user_model.objects.create_user("lee", password="pw-12345-xyz")
    r = client.post(reverse("login") + "?next=/usage/", {"username": "lee", "password": "pw-12345-xyz"})
    assert r["Location"] == "/usage/"


def test_login_for_an_account_without_a_profile_still_works(client, django_user_model):
    u = django_user_model.objects.create_user("old", password="pw-12345-xyz")
    UserProfile.objects.filter(user=u).delete()  # account predating profiles
    r = client.post(reverse("login"), {"username": "old", "password": "pw-12345-xyz"})
    assert r.status_code == 302 and r["Location"] == reverse("chat_home")
