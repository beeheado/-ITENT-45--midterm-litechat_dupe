"""Turns a user's saved settings into the system text sent to the model with every request."""
from .models import profile_for


def build_system_prompt(user):
    """The user's global system prompt followed by their memory items ("" when they have neither).

    Read at send time, so edits apply to existing chats. Memories go oldest first so the list reads naturally.
    """
    parts = []
    prompt = profile_for(user).system_prompt.strip()
    if prompt:
        parts.append(prompt)
    memories = list(user.memories.order_by("created_at", "id"))
    if memories:
        lines = "\n".join(f"- [{m.get_kind_display()}] {m.content}" for m in memories)
        parts.append(f"Things to remember about the user:\n{lines}")
    return "\n\n".join(parts)
