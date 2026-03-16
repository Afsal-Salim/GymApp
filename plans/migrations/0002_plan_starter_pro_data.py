# Generated data migration: Starter and Pro plans

from decimal import Decimal

from django.db import migrations


def add_plans(apps, schema_editor):
    Plan = apps.get_model("plans", "Plan")
    plans = [
        {"name": "Starter", "price": Decimal("499.00"), "duration": 28},
        {"name": "Pro", "price": Decimal("999.00"), "duration": 28},
    ]
    for data in plans:
        Plan.objects.get_or_create(
            name=data["name"],
            defaults={"price": data["price"], "duration": data["duration"]},
        )


def remove_plans(apps, schema_editor):
    Plan = apps.get_model("plans", "Plan")
    Plan.objects.filter(name__in=["Starter", "Pro"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_plans, remove_plans),
    ]
