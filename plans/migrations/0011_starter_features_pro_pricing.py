# Starter: marketing feature list. Pro: clear features, price 699.

from decimal import Decimal

from django.db import migrations


STARTER_FEATURES = [
    "Dynamic website for your gym",
    "5 ready-made themes (fully customizable)",
    "WhatsApp integration",
    "Basic client analytics",
    "Upload up to 10 images",
    "Email notifications for enquiries",
    "User activity insights",
]


def apply_changes(apps, schema_editor):
    Plan = apps.get_model("plans", "Plan")
    Feature = apps.get_model("plans", "Feature")
    active = "active"

    starter = Plan.objects.filter(name="Starter").first()
    if starter:
        Feature.objects.filter(plan=starter).delete()
        for name in STARTER_FEATURES:
            Feature.objects.create(plan=starter, name=name, record_status=active)

    pro = Plan.objects.filter(name="Pro").first()
    if pro:
        Feature.objects.filter(plan=pro).delete()
        pro.price = Decimal("699.00")
        pro.coming_soon = False
        pro.save()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0010_plan_internal_only_trial_plan"),
    ]

    operations = [
        migrations.RunPython(apply_changes, noop_reverse),
    ]
