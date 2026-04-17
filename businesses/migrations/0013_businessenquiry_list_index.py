from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("businesses", "0012_business_website_payload_split"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="businessenquiry",
            name="businesses__busines_ab4b1d_idx",
        ),
        migrations.AddIndex(
            model_name="businessenquiry",
            index=models.Index(
                fields=["business", "record_status", "-created_at"],
                name="biz_enquiry_biz_rs_crt_idx",
            ),
        ),
    ]
