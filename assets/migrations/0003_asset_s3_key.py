from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0002_asset_record_status_asset_updated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="s3_key",
            field=models.CharField(
                blank=True,
                default="",
                help_text="S3 object key (slug/uuid.ext) when stored in bucket.",
                max_length=1024,
            ),
        ),
    ]
