from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import MAX_PROMPT_CHARS


class SignupForm(UserCreationForm):
    first_name = forms.CharField(label="Display name (optional)", max_length=60, required=False)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name")


class SystemPromptForm(forms.Form):
    system_prompt = forms.CharField(required=False, max_length=MAX_PROMPT_CHARS, strip=False)
