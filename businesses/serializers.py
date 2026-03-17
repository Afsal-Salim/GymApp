from rest_framework import serializers

from subscriptions.models import Subscription

from .models import Business


class SubscriptionListSerializer(serializers.ModelSerializer):
    """Minimal subscription info for embedding in business list."""

    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "plan",
            "plan_name",
            "payment_id",
            "subscription_start_date",
            "subscription_end_date",
        )


class BusinessSerializer(serializers.ModelSerializer):
    """Full read serializer (includes owner id, email, username, subscriptions)."""

    owner_email = serializers.SerializerMethodField()
    owner_username = serializers.SerializerMethodField()
    subscriptions = SubscriptionListSerializer(many=True, read_only=True)

    class Meta:
        model = Business
        fields = (
            "id",
            "owner",
            "owner_email",
            "owner_username",
            "name",
            "slug",
            "description",
            "phone",
            "address",
            "subscriptions",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner", "created_at", "updated_at")

    def get_owner_email(self, obj):
        return obj.owner.email if obj.owner_id else None

    def get_owner_username(self, obj):
        return obj.owner.username if obj.owner_id else None


class BusinessCreateSerializer(serializers.ModelSerializer):
    """For creating a business; owner is set in the view."""

    class Meta:
        model = Business
        fields = ("name", "slug", "description", "phone", "address")

    def validate_slug(self, value):
        if Business.objects.filter(slug=value).exists():
            raise serializers.ValidationError("A business with this slug already exists.")
        return value

