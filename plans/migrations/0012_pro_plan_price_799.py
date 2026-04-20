# Pro plan: list price INR 799; ensure enabled for purchase (public API).

from decimal import Decimal

from django.db import migrations


def apply(apps, schema_editor):
    Plan = apps.get_model("plans", "Plan")
    pro = Plan.objects.filter(name="Pro").first()
    if pro:
        pro.price = Decimal("799.00")
        pro.coming_soon = False
        pro.internal_only = False
        pro.save()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0011_starter_features_pro_pricing"),
    ]

    operations = [
        migrations.RunPython(apply, noop_reverse),
    ]
