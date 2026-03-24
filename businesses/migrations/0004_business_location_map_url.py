from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("businesses", "0003_business_website_crystal"),
    ]

    operations = [
        migrations.AddField(
            model_name="business",
            name="location_map_url",
            field=models.URLField(blank=True, max_length=2000),
        ),
    ]
