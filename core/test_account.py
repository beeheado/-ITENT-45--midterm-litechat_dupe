import re
from datetime import datetime, timezone

import pytest
from django.urls import reverse

from core import ledger
from core.models import Wallet

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(django_user_model):
    u = django_user_model.objects.create_user("ann", password="pw", first_name="Ann", last_name="Lee")
    u.date_joined = datetime(2026, 3, 5, 12, 0, tzinfo=timezone.utc)
    u.save()
    return u


@pytest.fixture
def logged(client, user):
    client.force_login(user)
    client.user = user
    return client


def page(client):
    return client.get(reverse("account")).content.decode()


def test_login_required(client):
    r = client.get(reverse("account"))
    assert r.status_code == 302 and "/login/" in r["Location"]


def test_profile_card_shows_the_four_fields(logged, user):
    html = page(logged)
    for label in ("Display Name", "Username", "User ID", "Member Since"):
        assert label in html
    assert ">Ann Lee<" in html and ">ann<" in html and f"<dd>{user.pk}</dd>" in html
    assert "March 05, 2026" in html  # Month DD, YYYY


def test_display_name_falls_back_to_username(client, django_user_model):
    u = django_user_model.objects.create_user("plain", password="pw")
    client.force_login(u)
    html = page(client)
    assert "[Personal] plain" in html and "<dd>plain</dd>" in html


def test_billing_card_label_badge_and_currency_format(logged, user):
    ledger.credit(Wallet.objects.get(user=user).pk, 1_000_000, "topup")  # $1 welcome + $1 = $2.00
    html = page(logged)
    assert "[Personal] Ann Lee" in html and "ACTIVE" in html and "INACTIVE" not in html
    assert "AVAILABLE CREDIT" in html and "$2.00" in html


def test_inactive_user_shows_inactive_badge(client, django_user_model):
    u = django_user_model.objects.create_user("gone", password="pw")
    client.force_login(u)
    u.is_active = False
    u.save()
    # An inactive user cannot stay logged in, so check the template logic through the context instead.
    from django.template.loader import render_to_string

    html = render_to_string("account.html", {"user": u, "display_name": "gone", "balance_micros": 0, "profile": None})
    assert "INACTIVE" in html


def test_back_to_app_link_and_header_link(logged):
    html = page(logged)
    assert re.search(r'<p class="back"><a href="/">Back to App</a></p>', html)
    assert 'href="/account/"' in html  # header link


def test_signup_collects_an_optional_display_name(client):
    r = client.post(reverse("signup"), {"username": "newbie", "first_name": "Nia Novak",
                                        "password1": "s3cret-Pass!9", "password2": "s3cret-Pass!9"})
    assert r.status_code == 302
    assert "[Personal] Nia Novak" in page(client)


def test_signup_still_works_without_a_display_name(client):
    r = client.post(reverse("signup"), {"username": "quiet", "password1": "s3cret-Pass!9", "password2": "s3cret-Pass!9"})
    assert r.status_code == 302 and "[Personal] quiet" in page(client)
