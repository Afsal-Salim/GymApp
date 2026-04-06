from django.conf import settings
from rest_framework import serializers

from core.s3_gym_images import gym_image_browser_url

from .models import Asset


class AssetSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = (
            "id",
            "business",
            "image_url",
            "s3_key",
            "asset_type",
            "uploaded_at",
            "updated_at",
            "record_status",
        )
        read_only_fields = fields

    def get_image_url(self, obj):
        key = (obj.s3_key or "").strip()
        bucket = (getattr(settings, "AWS_S3_GYM_IMAGES_BUCKET", "") or "").strip()
        if key and bucket:
            url = gym_image_browser_url(key)
            if url:
                return url
        return obj.image_url

