from rest_framework import serializers

from plans.serializers import PlanSerializer

from .models import Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"


class CurrentSubscriptionSerializer(serializers.ModelSerializer):
    """Active subscription for owner-facing API (plan includes features)."""

    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "payment_id",
            "subscription_start_date",
            "subscription_end_date",
            "plan",
        )

