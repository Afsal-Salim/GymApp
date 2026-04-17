import django.db.models.deletion
from django.db import migrations, models


def copy_json_to_payload_table(apps, schema_editor):
    Business = apps.get_model("businesses", "Business")
    Payload = apps.get_model("businesses", "BusinessWebsitePayload")
    for b in Business.objects.all().iterator():
        wt = b.website_theme if isinstance(getattr(b, "website_theme", None), dict) else {}
        wc = b.website_content if isinstance(getattr(b, "website_content", None), dict) else {}
        Payload.objects.create(business_id=b.pk, website_theme=wt, website_content=wc)


def merge_payload_back_to_business(apps, schema_editor):
    Business = apps.get_model("businesses", "Business")
    Payload = apps.get_model("businesses", "BusinessWebsitePayload")
    for p in Payload.objects.all().iterator():
        Business.objects.filter(pk=p.business_id).update(
            website_theme=p.website_theme or {},
            website_content=p.website_content or {},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("businesses", "0011_crystallead_business_created_at_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="BusinessWebsitePayload",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("website_theme", models.JSONField(blank=True, default=dict)),
                ("website_content", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "business",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="website_payload",
                        to="businesses.business",
                    ),
                ),
            ],
        ),
        migrations.RunPython(copy_json_to_payload_table, merge_payload_back_to_business),
        migrations.RemoveField(
            model_name="business",
            name="website_theme",
        ),
        migrations.RemoveField(
            model_name="business",
            name="website_content",
        ),
        migrations.AddIndex(
            model_name="business",
            index=models.Index(
                fields=["owner", "record_status"],
                name="business_owner_status_idx",
            ),
        ),
    ]
