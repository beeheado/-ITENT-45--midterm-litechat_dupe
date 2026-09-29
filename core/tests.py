import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_signup_logs_user_in(client):
    r = client.post(reverse("signup"), {"username": "ann", "password1": "s3cret-Pass!9", "password2": "s3cret-Pass!9"})
    assert r.status_code == 302
    assert client.get(reverse("chat_home")).status_code == 200


@pytest.mark.django_db
def test_login_required(client):
    r = client.get(reverse("chat_home"))
    assert r.status_code == 302 and "/login/" in r["Location"]


@pytest.mark.django_db
def test_login_and_logout(client, django_user_model):
    django_user_model.objects.create_user("bob", password="pw-12345-xyz")
    assert client.post(reverse("login"), {"username": "bob", "password": "pw-12345-xyz"}).status_code == 302
    assert client.post(reverse("logout")).status_code == 302
    assert client.get(reverse("chat_home")).status_code == 302
