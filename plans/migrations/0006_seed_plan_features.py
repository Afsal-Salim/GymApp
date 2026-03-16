# Data migration: add features per plan (Starter: 4, Pro: 10)

from django.db import migrations


STARTER_FEATURES = [
    "WhatsApp chat",
    "Online payments",
    "Member management",
    "Attendance tracking",
]

PRO_FEATURES = [
    "WhatsApp chat",
    "Online payments",
    "Member management",
    "Attendance tracking",
    "Class scheduling",
    "Reports & analytics",
    "SMS notifications",
    "Multiple branch support",
    "API access",
    "Priority support",
]


def add_features(apps, schema_editor):
    Plan = apps.get_model("plans", "Plan")
    Feature = apps.get_model("plans", "Feature")
    starter = Plan.objects.filter(name="Starter").first()
    pro = Plan.objects.filter(name="Pro").first()
    if starter:
        for name in STARTER_FEATURES:
            Feature.objects.get_or_create(plan=starter, name=name)
    if pro:
        for name in PRO_FEATURES:
            Feature.objects.get_or_create(plan=pro, name=name)


def remove_features(apps, schema_editor):
    Feature = apps.get_model("plans", "Feature")
    Feature.objects.filter(
        name__in=STARTER_FEATURES + PRO_FEATURES
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0005_feature_fk_to_plan"),
    ]

    operations = [
        migrations.RunPython(add_features, remove_features),
    ]
