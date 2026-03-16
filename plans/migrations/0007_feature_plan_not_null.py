import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0006_seed_plan_features"),
    ]

    operations = [
        migrations.AlterField(
            model_name="feature",
            name="plan",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="features",
                to="plans.plan",
                null=False,
            ),
        ),
    ]
