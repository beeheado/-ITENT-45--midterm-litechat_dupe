from django.db import migrations

# The proxy's models think before answering, and thinking counts against max_tokens. At 1024 a real question could
# spend the whole budget reasoning and produce no answer. Measured on the real proxy: "explain X in detail" needs
# 8000+ tokens on the OpenAI interface, simple questions need under 300. Only rows still at the old default change.
OLD, NEW = 1024, 8192


def raise_budget(apps, schema_editor):
    apps.get_model("core", "LLMModel").objects.filter(max_output_tokens=OLD).update(max_output_tokens=NEW)


def restore_budget(apps, schema_editor):
    apps.get_model("core", "LLMModel").objects.filter(max_output_tokens=NEW).update(max_output_tokens=OLD)


class Migration(migrations.Migration):
    dependencies = [("core", "0003_message_finish_reason")]
    operations = [migrations.RunPython(raise_budget, restore_budget)]
