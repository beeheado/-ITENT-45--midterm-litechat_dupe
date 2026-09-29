"""The /account/ page and its POST actions. Kept apart from views.py (chat) so each file stays readable."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import MemoryForm, SystemPromptForm
from .models import MAX_MEMORY_CHARS, MAX_MEMORY_ITEMS, MAX_PROMPT_CHARS, MemoryItem, profile_for


def display_name(user):
    return user.get_full_name().strip() or user.username


@login_required
def account(request):
    return render(request, "account.html", {
        "profile": profile_for(request.user),
        "display_name": display_name(request.user),
        "memories": request.user.memories.all(),
        "memory_kinds": MemoryItem.KINDS,
    })


@login_required
@require_POST
def save_prompt(request):
    form = SystemPromptForm(request.POST)
    if form.is_valid():
        profile = profile_for(request.user)
        profile.system_prompt = form.cleaned_data["system_prompt"]
        profile.save(update_fields=["system_prompt"])
        messages.success(request, "System prompt saved.")
    else:
        messages.error(request, f"The prompt is too long (max {MAX_PROMPT_CHARS} characters). Nothing was saved.")
    return redirect("account")


@login_required
@require_POST
def add_memory(request):
    form = MemoryForm(request.POST)
    if not form.is_valid():
        messages.error(request, f"Enter some text for the memory (up to {MAX_MEMORY_CHARS} characters) and pick a type.")
    elif request.user.memories.count() >= MAX_MEMORY_ITEMS:
        messages.error(request, f"You can keep up to {MAX_MEMORY_ITEMS} memory items. Delete one to add another.")
    else:
        MemoryItem.objects.create(user=request.user, **form.cleaned_data)
        messages.success(request, "Memory added.")
    return redirect("account")


@login_required
@require_POST
def delete_memory(request, pk):
    get_object_or_404(MemoryItem, pk=pk, user=request.user).delete()
    messages.success(request, "Memory deleted.")
    return redirect("account")


@login_required
@require_POST
def set_auto_memory(request):
    """The switch is a checkbox: an unchecked box sends nothing, so absence means off."""
    profile = profile_for(request.user)
    profile.auto_memory = "auto_memory" in request.POST
    profile.save(update_fields=["auto_memory"])
    return redirect("account")
