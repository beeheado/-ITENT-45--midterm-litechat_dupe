from django.db import migrations

# Placeholder rate card in micro-credits per million tokens (editable in admin).
# The proxy publishes no prices, so these are our own; see study 001.
SEED = [
    ("openai", "gpt-5.6-luna", "GPT-5.6 Luna", 250_000, 2_000_000),
    ("anthropic", "claude-haiku-4-5-20251001", "Claude Haiku 4.5", 1_000_000, 5_000_000),
    ("google", "gemini-3.8-flash", "Gemini 3.8 Flash", 300_000, 2_500_000),
]


def seed(apps, schema_editor):
    LLMModel = apps.get_model("core", "LLMModel")
    for provider, model_id, name, price_in, price_out in SEED:
        LLMModel.objects.update_or_create(
            model_id=model_id,
            defaults=dict(
                provider=provider,
                display_name=name,
                input_price_micros_per_mtok=price_in,
                output_price_micros_per_mtok=price_out,
                max_output_tokens=1024,
            ),
        )


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial_models")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
