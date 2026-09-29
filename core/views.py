import json
from datetime import timedelta

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import ledger
from .models import Conversation, LedgerEntry, LLMModel, Message
from .providers import get_adapter
from .providers.types import ChatMessage, ChatRequest, Done, Error, ReasoningDelta, TextDelta, Usage

PENDING_WINDOW = timedelta(minutes=3)


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            login(request, form.save())
            return redirect("chat_home")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


def _sidebar(request):
    return Conversation.objects.filter(user=request.user)


@login_required
def chat_home(request):
    return render(request, "chat.html", {"conversations": _sidebar(request), "conversation": None})


@login_required
@require_POST
def new_conversation(request):
    first = LLMModel.objects.filter(is_active=True).first()
    conv = Conversation.objects.create(user=request.user, model=first)
    return redirect("conversation", pk=conv.pk)


@login_required
def conversation(request, pk):
    conv = get_object_or_404(Conversation, pk=pk, user=request.user)
    return render(request, "chat.html", {
        "conversations": _sidebar(request),
        "conversation": conv,
        "chat_messages": conv.messages.select_related("model"),
        "models": LLMModel.objects.filter(is_active=True),
    })


def _ndjson(obj):
    return json.dumps(obj) + "\n"


def _history(conv):
    """Messages the model should see: everything that completed, plus the new user turn."""
    return [
        ChatMessage(m.role, m.content)
        for m in conv.messages.all()
        if m.content and (m.role == "user" or m.status == "complete")
    ]


@login_required
@require_POST
def send(request, pk):
    conv = get_object_or_404(Conversation, pk=pk, user=request.user)
    content = request.POST.get("content", "").strip()
    model = LLMModel.objects.filter(pk=request.POST.get("model") or 0, is_active=True).first()
    if not content:
        return JsonResponse({"error": "Type a message first."}, status=400)
    if model is None:
        return JsonResponse({"error": "Pick a model."}, status=400)

    # One reply at a time per chat. A pending reply older than the window is stale (crashed request).
    in_flight = conv.messages.filter(role="assistant", status="pending", created_at__gte=timezone.now() - PENDING_WINDOW)
    if in_flight.exists():
        return JsonResponse({"error": "Wait for the current reply to finish."}, status=409)

    wallet = request.user.wallet
    history = _history(conv) + [ChatMessage("user", content)]
    try:
        ledger.ensure_can_afford(wallet, ledger.estimate_reserve(model, history))
    except ledger.InsufficientBalance:
        return JsonResponse({"error": "Not enough balance for this message. Ask an admin for credits."}, status=402)

    Message.objects.create(conversation=conv, role="user", content=content)
    if conv.title == "New chat":
        conv.title = content[:40]
    conv.model = model
    conv.save()
    reply = Message.objects.create(conversation=conv, role="assistant", model=model, status="pending")

    req = ChatRequest(model.model_id, history, model.max_output_tokens)
    return StreamingHttpResponse(
        _stream_reply(get_adapter(model.provider), req, reply, wallet), content_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _stream_reply(adapter, req, reply, wallet):
    text, reasoning, usage, error, finished = [], [], None, "", False
    try:
        for ev in adapter.stream(req):
            if isinstance(ev, TextDelta):
                text.append(ev.text)
                yield _ndjson({"t": "text", "v": ev.text})
            elif isinstance(ev, ReasoningDelta):
                reasoning.append(ev.text)
                yield _ndjson({"t": "reasoning", "v": ev.text})
            elif isinstance(ev, Usage):
                usage = ev
            elif isinstance(ev, Error):
                error = ev.message
            elif isinstance(ev, Done):
                finished = True
    except GeneratorExit:
        # Client went away mid-stream: usage is unknown, so save what we have and don't bill.
        ledger.finalize_message(reply, content="".join(text), reasoning="".join(reasoning),
                                usage=None, status="cancelled", error="Stopped before the reply finished.")
        raise
    except Exception:  # never leave a message pending
        error = error or "Unexpected error while streaming."
    status = "complete" if finished and not error else "failed"
    ledger.finalize_message(reply, content="".join(text), reasoning="".join(reasoning),
                            usage=usage, status=status, error=error)
    wallet.refresh_from_db()
    yield _ndjson({"t": "done", "status": reply.status, "error": reply.error, "cost": reply.cost_micros,
                   "input": reply.input_tokens, "output": reply.output_tokens, "balance": wallet.balance_micros})


@login_required
@require_POST
def rename(request, pk):
    conv = get_object_or_404(Conversation, pk=pk, user=request.user)
    title = request.POST.get("title", "").strip()[:200]
    if title:
        conv.title = title
        conv.save(update_fields=["title"])
    return redirect("conversation", pk=conv.pk)


@login_required
@require_POST
def delete(request, pk):
    get_object_or_404(Conversation, pk=pk, user=request.user).delete()
    return redirect("chat_home")


@login_required
def usage(request):
    entries = LedgerEntry.objects.filter(wallet__user=request.user).select_related("message__conversation", "message__model")
    spent = -sum(e.amount_micros for e in entries if e.kind == "charge")
    return render(request, "usage.html", {"entries": entries, "spent_micros": spent})
