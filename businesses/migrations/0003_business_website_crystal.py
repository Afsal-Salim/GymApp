# Crystal website builder (theme + content JSON)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("businesses", "0002_crystal_lead"),
    ]

    operations = [
        migrations.AddField(
            model_name="business",
            name="website_theme",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="business",
            name="website_content",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
