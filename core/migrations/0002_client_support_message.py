# Generated manually for ClientSupportMessage

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0001_initial"),
        ("core", "0001_site_enquiry"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientSupportMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(
                        choices=[("support", "Support"), ("feedback", "Feedback")],
                        db_index=True,
                        max_length=16,
                    ),
                ),
                ("subject", models.CharField(blank=True, max_length=200)),
                ("message", models.TextField(max_length=5000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="support_messages",
                        to="authentication.customer",
                    ),
                ),
            ],
            options={
                "verbose_name": "Client support / feedback",
                "verbose_name_plural": "Client support & feedback",
                "ordering": ["-created_at"],
            },
        ),
    ]
