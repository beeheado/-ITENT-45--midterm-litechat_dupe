from django.conf import settings
from django.db import migrations


def backfill(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("core", "UserProfile")
    for user in User.objects.filter(profile__isnull=True):
        UserProfile.objects.create(user=user)


class Migration(migrations.Migration):
    dependencies = [("core", "0006_user_profile_and_memory")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
