"""The /account/ page and its POST actions. Kept apart from views.py (chat) so each file stays readable."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import profile_for


def display_name(user):
    return user.get_full_name().strip() or user.username


@login_required
def account(request):
    return render(request, "account.html", {
        "profile": profile_for(request.user),
        "display_name": display_name(request.user),
    })
