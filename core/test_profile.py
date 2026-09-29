import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from core.models import MAX_MEMORY_CHARS, MemoryItem, UserProfile, profile_for

pytestmark = pytest.mark.django_db


def test_profile_is_created_with_the_account_and_has_defaults(django_user_model):
    u = django_user_model.objects.create_user("ann", password="pw")
    p = UserProfile.objects.get(user=u)
    assert (p.system_prompt, p.auto_memory, p.default_app) == ("", False, "chat")


def test_profile_for_creates_a_missing_profile_once(django_user_model):
    u = django_user_model.objects.create_user("ann", password="pw")
    UserProfile.objects.filter(user=u).delete()  # simulate an account from before profiles existed
    first = profile_for(u)
    assert profile_for(u).pk == first.pk and UserProfile.objects.filter(user=u).count() == 1


def test_profiles_and_memories_are_per_user(django_user_model):
    a = django_user_model.objects.create_user("ann", password="pw")
    b = django_user_model.objects.create_user("bob", password="pw")
    pa = profile_for(a)
    pa.system_prompt = "Be brief."
    pa.save()
    MemoryItem.objects.create(user=a, kind="fact", content="Ann likes tea")
    assert profile_for(b).system_prompt == "" and not b.memories.exists()
    assert list(a.memories.values_list("content", flat=True)) == ["Ann likes tea"]


def test_memories_are_newest_first_with_source_and_kind_labels(django_user_model):
    u = django_user_model.objects.create_user("ann", password="pw")
    MemoryItem.objects.create(user=u, content="old")
    new = MemoryItem.objects.create(user=u, kind="goal", content="new", source="ai")
    assert u.memories.first() == new
    assert (new.get_kind_display(), new.get_source_display()) == ("Goal", "AI")
    assert MemoryItem._meta.get_field("content").max_length == MAX_MEMORY_CHARS


def test_users_with_ledger_history_cannot_be_deleted(django_user_model):
    """The append-only ledger protects wallets (PROTECT), so an account with money history is not deletable.
    Profiles and memories cascade with their user, but that is only reachable once the ledger allows deletion."""
    from django.db.models import ProtectedError

    u = django_user_model.objects.create_user("ann", password="pw")  # has the welcome-grant ledger entry
    with pytest.raises(ProtectedError):
        u.delete()
    assert UserProfile.objects.filter(user=u).exists()


@pytest.mark.django_db(transaction=True)
def test_backfill_migration_creates_profiles_for_existing_users(django_user_model):
    """Accounts created before UserProfile existed get one when the backfill migration runs."""
    u = django_user_model.objects.create_user("old", password="pw")
    UserProfile.objects.filter(user=u).delete()
    executor = MigrationExecutor(connection)
    executor.migrate([("core", "0006_user_profile_and_memory")])  # step back to before the backfill
    executor = MigrationExecutor(connection)
    executor.migrate([("core", "0007_backfill_profiles")])
    assert UserProfile.objects.filter(user=u).count() == 1
