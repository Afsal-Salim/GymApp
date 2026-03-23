# Generated manually for Crystal leads / WhatsApp analytics

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("businesses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CrystalLead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "lead_type",
                    models.CharField(
                        choices=[
                            ("join_now", "Join now"),
                            ("book_free_trial", "Book free trial"),
                            ("plan_visit", "Plan your visit"),
                            ("whatsapp_click", "WhatsApp click"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("submitted_at_ms", models.BigIntegerField(blank=True, null=True)),
                (
                    "quantity",
                    models.PositiveSmallIntegerField(
                        default=1,
                        help_text="Usually 1; for whatsapp_click equals click_count (capped).",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "business",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="crystal_leads",
                        to="businesses.business",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="crystallead",
            index=models.Index(
                fields=["business", "lead_type", "-created_at"],
                name="crystallead_biz_type_created",
            ),
        ),
    ]
