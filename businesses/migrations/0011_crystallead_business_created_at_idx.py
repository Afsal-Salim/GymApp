from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("businesses", "0010_business_logo_s3_key"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="crystallead",
            index=models.Index(
                fields=["business", "created_at"],
                name="crystallead_biz_created_idx",
            ),
        ),
    ]
