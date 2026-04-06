from django.db import migrations, models


def seed_trial_plan(apps, schema_editor):
    Plan = apps.get_model("plans", "Plan")
    if Plan.objects.filter(name="7-day free trial").exists():
        return
    Plan.objects.create(
        name="7-day free trial",
        price=0,
        first_activation_price=None,
        currency="INR",
        duration=7,
        coming_soon=False,
        record_status="active",
        internal_only=True,
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0009_plan_activation_coming_soon"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="internal_only",
            field=models.BooleanField(
                default=False,
                help_text="When true, hidden from public plan list and not purchasable via payment APIs.",
            ),
        ),
        migrations.RunPython(seed_trial_plan, noop_reverse),
    ]
