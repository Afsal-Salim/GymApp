from django.db import migrations


def set_crystal_admin_active(apps, schema_editor):
    Customer = apps.get_model("authentication", "Customer")
    Customer.objects.filter(email__iexact="crystal.gym.in@gmail.com").update(
        record_status="active",
        role=0,
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0009_customer_role"),
    ]

    operations = [
        migrations.RunPython(set_crystal_admin_active, noop_reverse),
    ]
