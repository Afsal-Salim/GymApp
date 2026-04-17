from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("businesses", "0009_phone_ten_digits"),
    ]

    operations = [
        migrations.AddField(
            model_name="business",
            name="logo_s3_key",
            field=models.CharField(
                blank=True,
                default="",
                help_text="S3 object key for owner-uploaded logo (logos/<slug>/<uuid>.ext). Empty if using website_content only.",
                max_length=1024,
            ),
        ),
    ]
