# Generated manually for Google sign-in

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0005_add_emailotp_purpose"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="auth_provider",
            field=models.CharField(
                choices=[("email", "Email"), ("google", "Google")],
                default="email",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="customer",
            name="google_id",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
    ]
