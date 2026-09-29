"""Turns a user's saved settings into the system text sent to the model with every request."""
from .models import profile_for


def build_system_prompt(user):
    """The user's global system prompt ("" when they have none). Read at send time, so edits apply to existing chats."""
    return profile_for(user).system_prompt.strip()
