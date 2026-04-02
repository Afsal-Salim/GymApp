from django.db import migrations


def set_thakathakatha_admin(apps, schema_editor):
    Customer = apps.get_model("authentication", "Customer")
    Customer.objects.filter(email__iexact="thakathakatha123@gmail.com").update(role=0)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0010_crystal_admin_active"),
    ]

    operations = [
        migrations.RunPython(set_thakathakatha_admin, noop_reverse),
    ]
