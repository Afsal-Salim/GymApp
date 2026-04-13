# Generated manually for public active-subscription query performance.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0002_subscription_created_at_subscription_record_status_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="subscription",
            index=models.Index(
                fields=["business", "record_status", "subscription_end_date"],
                name="sub_biz_status_end_idx",
            ),
        ),
    ]
