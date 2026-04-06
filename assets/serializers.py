from rest_framework import serializers

from .models import Asset


class AssetSerializer(serializers.ModelSerializer):
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

