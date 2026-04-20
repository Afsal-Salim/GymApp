# Pro plan feature list (marketing copy; price unchanged — see 0012).

from django.db import migrations


PRO_FEATURES = [
    (
        "Everything in Base — Dynamic website, themes, WhatsApp, analytics, "
        "enquiry emails, and visitor insights."
    ),
    (
        "3× image upload vs Base — Triple the gallery and media capacity for photos, "
        "coaches, and hero sections."
    ),
    (
        "Premium templates — Extra client page layouts and styles beyond the Base set."
    ),
    (
        "SMS notifications for new leads — Get a text alert when someone submits a lead "
        "so you can respond faster."
    ),
]


def apply(apps, schema_editor):
    Plan = apps.get_model("plans", "Plan")
    Feature = apps.get_model("plans", "Feature")
    active = "active"

    pro = Plan.objects.filter(name="Pro").first()
    if not pro:
        return

    Feature.objects.filter(plan=pro).delete()
    for name in PRO_FEATURES:
        Feature.objects.create(plan=pro, name=name, record_status=active)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0012_pro_plan_price_799"),
    ]

    operations = [
        migrations.RunPython(apply, noop_reverse),
    ]
