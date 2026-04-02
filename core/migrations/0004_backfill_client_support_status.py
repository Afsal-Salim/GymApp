from django.db import migrations


def forwards(apps, schema_editor):
    ClientSupportMessage = apps.get_model("core", "ClientSupportMessage")
    for row in ClientSupportMessage.objects.filter(kind="support"):
        if row.support_status in (None, ""):
            row.support_status = "open"
            row.save(update_fields=["support_status"])
    for row in ClientSupportMessage.objects.filter(kind="feedback"):
        if row.feedback_status in (None, ""):
            row.feedback_status = "open"
            row.save(update_fields=["feedback_status"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_clientsupportmessage_feedback_status_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
