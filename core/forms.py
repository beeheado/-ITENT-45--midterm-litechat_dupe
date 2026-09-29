from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import MAX_MEMORY_CHARS, MAX_PROMPT_CHARS, MemoryItem


class SignupForm(UserCreationForm):
    first_name = forms.CharField(label="Display name (optional)", max_length=60, required=False)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name")


class SystemPromptForm(forms.Form):
    system_prompt = forms.CharField(required=False, max_length=MAX_PROMPT_CHARS, strip=False)


class MemoryForm(forms.Form):
    kind = forms.ChoiceField(choices=MemoryItem.KINDS)
    content = forms.CharField(max_length=MAX_MEMORY_CHARS, strip=True)  # required: blank is rejected
