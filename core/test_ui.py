"""Guards for usability: the visual refresh must not remove or break any control the flow depends on."""
import re
import shutil
import subprocess

import pytest
from django.urls import reverse

from core.models import Conversation, LLMModel, Message

pytestmark = pytest.mark.django_db


@pytest.fixture
def logged(client, django_user_model):
    user = django_user_model.objects.create_user("ann", password="pw")
    client.force_login(user)
    client.user = user
    return client


@pytest.fixture
def chat_page(logged):
    model = LLMModel.objects.get(provider="anthropic")
    conv = Conversation.objects.create(user=logged.user, model=model, title="Hello")
    Message.objects.create(conversation=conv, role="assistant", model=model, content="hi", reasoning="why")
    return logged.get(reverse("conversation", args=[conv.pk])).content.decode()


def test_every_page_is_responsive_and_themed(logged, chat_page):
    pages = [chat_page, logged.get(reverse("usage")).content.decode(), logged.get(reverse("chat_home")).content.decode()]
    for html in pages:
        assert 'name="viewport"' in html and 'name="color-scheme"' in html and "style.css" in html
    for name in ("login", "signup"):
        assert 'name="viewport"' in logged.__class__().get(reverse(name)).content.decode()


def test_chat_controls_still_present(chat_page):
    for needle in ('id="composer"', 'name="content"', 'name="model"', 'id="send"', 'id="messages"',
                   'name="csrfmiddlewaretoken"', 'action="/c/', 'aria-label="Message"', 'aria-label="Model"',
                   'role="alert"', "Rename", "Delete", "+ New chat", "Reasoning", 'class="copy"'):
        assert needle in chat_page, needle
    assert chat_page.count("<option") == 3  # one per active model


def test_home_lists_models_with_prices_and_offers_new_chat(logged):
    html = logged.get(reverse("chat_home")).content.decode()
    for name in ("Claude Haiku 4.5", "Gemini 3.8 Flash", "GPT-5.6 Luna"):
        assert name in html
    assert "Start a new chat" in html and "$5.00 out per 1M tokens" in html


def test_balance_pill_links_to_usage(logged):
    html = logged.get(reverse("chat_home")).content.decode()
    assert re.search(r'<a href="/usage/" class="balance"', html)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_inline_chat_script_is_valid_javascript(chat_page, tmp_path):
    js = re.search(r"<script>(.*?)</script>", chat_page, re.S).group(1)
    f = tmp_path / "chat.js"
    f.write_text(js)
    result = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_stylesheet_is_discoverable_by_staticfiles():
    """Regression: static/ at the project root was not registered, so the site rendered unstyled (404 on /static/style.css)."""
    from django.contrib.staticfiles import finders

    path = finders.find("style.css")
    assert path, "style.css is not discoverable by staticfiles"
    assert "--accent" in open(path).read()
