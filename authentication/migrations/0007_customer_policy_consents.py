from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0006_add_google_auth_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="privacy_policy_accepted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="customer",
            name="user_content_policy_accepted",
            field=models.BooleanField(default=False),
        ),
    ]
