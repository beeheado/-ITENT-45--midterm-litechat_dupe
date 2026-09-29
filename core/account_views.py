"""The /account/ page and its POST actions. Kept apart from views.py (chat) so each file stays readable."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import SystemPromptForm
from .models import MAX_PROMPT_CHARS, profile_for


def display_name(user):
    return user.get_full_name().strip() or user.username


@login_required
def account(request):
    return render(request, "account.html", {
        "profile": profile_for(request.user),
        "display_name": display_name(request.user),
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
