import json

import pytest
from django.urls import reverse

from core import ledger, views
from core.models import Conversation, LedgerEntry, LLMModel, Message, Wallet
from core.providers.types import ChatRequest, Done, Error, ReasoningDelta, TextDelta, Usage

pytestmark = pytest.mark.django_db


class FakeAdapter:
    def __init__(self, events):
        self.events, self.requests = events, []

    def stream(self, req):
        self.requests.append(req)
        yield from self.events


GOOD = [ReasoningDelta("thinking"), TextDelta("po"), TextDelta("ng"), Usage(208, 17), Done("stop")]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user("ann", password="pw")


@pytest.fixture
def logged(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def model():
    return LLMModel.objects.get(model_id="claude-haiku-4-5-20251001")


@pytest.fixture
def conv(user, model):
    return Conversation.objects.create(user=user, model=model)


def use_adapter(monkeypatch, events):
    fake = FakeAdapter(events)
    monkeypatch.setattr(views, "get_adapter", lambda provider: fake)
    return fake


def post(client, conv, model, content="ping"):
    r = client.post(reverse("send", args=[conv.pk]), {"content": content, "model": model.pk})
    body = b"".join(r.streaming_content).decode() if getattr(r, "streaming", False) else r.content.decode()
    return r, body


def events_of(body):
    return [json.loads(line) for line in body.splitlines() if line]


def test_streams_saves_and_charges(logged, conv, model, user, monkeypatch):
    fake = use_adapter(monkeypatch, GOOD)
    r, body = post(logged, conv, model)
    ev = events_of(body)
    assert r.status_code == 200
    assert [e["t"] for e in ev] == ["reasoning", "text", "text", "done"]
    assert "".join(e["v"] for e in ev if e["t"] == "text") == "pong"
    done = ev[-1]
    assert done["status"] == "complete" and done["cost"] == 293 and done["balance"] == 1_000_000 - 293

    user_msg, reply = Message.objects.filter(conversation=conv)
    assert (user_msg.role, user_msg.content) == ("user", "ping")
    assert (reply.content, reply.reasoning, reply.status, reply.model) == ("pong", "thinking", "complete", model)
    assert LedgerEntry.objects.filter(message=reply, kind="charge", amount_micros=-293).count() == 1
    assert fake.requests[0].messages[-1].content == "ping"
    conv.refresh_from_db()
    assert conv.title == "ping"


def test_insufficient_balance_blocks_call_and_saves_nothing(logged, conv, model, user, monkeypatch):
    fake = use_adapter(monkeypatch, GOOD)
    ledger.credit(Wallet.objects.get(user=user).pk, -999_999, "adjustment")
    r, body = post(logged, conv, model)
    assert r.status_code == 402 and "balance" in json.loads(body)["error"]
    assert not fake.requests and Message.objects.count() == 0


def test_provider_error_midstream_is_failed_and_free(logged, conv, model, user, monkeypatch):
    use_adapter(monkeypatch, [TextDelta("par"), Error("upstream", "boom", 502)])
    r, body = post(logged, conv, model)
    done = events_of(body)[-1]
    assert done["status"] == "failed" and done["error"] == "boom" and done["cost"] == 0
    reply = Message.objects.get(conversation=conv, role="assistant")
    assert reply.content == "par" and reply.status == "failed"
    assert Wallet.objects.get(user=user).balance_micros == 1_000_000
    assert LedgerEntry.objects.filter(kind="charge").count() == 0


def test_stream_that_never_finishes_is_failed(logged, conv, model, monkeypatch):
    use_adapter(monkeypatch, [TextDelta("hi")])  # no Done, no Usage
    _, body = post(logged, conv, model)
    assert events_of(body)[-1]["status"] == "failed"


def test_client_disconnect_saves_partial_and_does_not_bill(conv, model, user):
    reply = Message.objects.create(conversation=conv, role="assistant", model=model, status="pending")
    gen = views._stream_reply(FakeAdapter(GOOD), ChatRequest("m", []), reply, user.wallet)
    next(gen)
    gen.close()  # what the server does when the browser goes away
    reply.refresh_from_db()
    assert reply.status == "cancelled" and reply.cost_micros == 0
    assert Wallet.objects.get(user=user).balance_micros == 1_000_000


def test_history_sent_to_model_skips_failed_replies(logged, conv, model, monkeypatch):
    Message.objects.create(conversation=conv, role="user", content="q1")
    Message.objects.create(conversation=conv, role="assistant", content="a1", model=model, status="complete")
    Message.objects.create(conversation=conv, role="user", content="q2")
    Message.objects.create(conversation=conv, role="assistant", content="junk", model=model, status="failed")
    fake = use_adapter(monkeypatch, GOOD)
    post(logged, conv, model, "q3")
    assert [(m.role, m.content) for m in fake.requests[0].messages] == [
        ("user", "q1"), ("assistant", "a1"), ("user", "q2"), ("user", "q3"),
    ]


def test_empty_message_and_bad_model_rejected(logged, conv, model, monkeypatch):
    use_adapter(monkeypatch, GOOD)
    assert post(logged, conv, model, "   ")[0].status_code == 400
    r = logged.post(reverse("send", args=[conv.pk]), {"content": "hi", "model": 99999})
    assert r.status_code == 400


def test_cannot_use_someone_elses_conversation(client, django_user_model, conv, model, monkeypatch):
    use_adapter(monkeypatch, GOOD)
    client.force_login(django_user_model.objects.create_user("eve", password="pw"))
    assert client.get(reverse("conversation", args=[conv.pk])).status_code == 404
    assert client.post(reverse("send", args=[conv.pk]), {"content": "x", "model": model.pk}).status_code == 404


def test_pages_render(logged, conv, model, monkeypatch):
    use_adapter(monkeypatch, GOOD)
    post(logged, conv, model, "hello <b>there</b>")
    page = logged.get(reverse("conversation", args=[conv.pk])).content.decode()
    assert "hello &lt;b&gt;there&lt;/b&gt;" in page  # user content is escaped
    assert "Reasoning" in page and "Claude Haiku 4.5" in page
    assert logged.get(reverse("chat_home")).status_code == 200
    r = logged.post(reverse("new_conversation"))
    assert r.status_code == 302 and Conversation.objects.count() == 2


def test_second_send_while_reply_pending_is_rejected(logged, conv, model, monkeypatch):
    fake = use_adapter(monkeypatch, GOOD)
    Message.objects.create(conversation=conv, role="assistant", model=model, status="pending")
    r, body = post(logged, conv, model)
    assert r.status_code == 409 and not fake.requests


def test_stale_pending_reply_does_not_block_forever(logged, conv, model, monkeypatch):
    from datetime import timedelta

    from django.utils import timezone

    use_adapter(monkeypatch, GOOD)
    old = Message.objects.create(conversation=conv, role="assistant", model=model, status="pending")
    Message.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(minutes=10))
    r, _ = post(logged, conv, model)
    assert r.status_code == 200
