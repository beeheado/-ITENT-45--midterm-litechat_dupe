from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class SignupForm(UserCreationForm):
    first_name = forms.CharField(label="Display name (optional)", max_length=60, required=False)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name")
