from rest_framework import serializers

from businesses.models import Business
from plans.models import Plan

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class CreateOrderSerializer(serializers.Serializer):
    """
    Payload from frontend: plan_id, email, business_slug (slug).
    Use either plan_id or amount for the order amount.
    """

    email = serializers.EmailField(write_only=True)
    business_slug = serializers.SlugField(write_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(), required=False, allow_null=True
    )
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    currency = serializers.CharField(max_length=10, default="INR", required=False)

    def validate(self, attrs):
        slug = attrs["business_slug"]
        try:
            attrs["business_id"] = Business.objects.get(slug=slug)
        except Business.DoesNotExist:
            raise serializers.ValidationError(
                {"business_slug": "No business found for this slug."}
            )

        # Amount: exactly one of plan_id or amount
        plan = attrs.get("plan_id")
        amount = attrs.get("amount")
        if plan and amount is not None:
            raise serializers.ValidationError(
                "Provide either plan_id or amount, not both."
            )
        if not plan and amount is None:
            raise serializers.ValidationError("Provide plan_id or amount.")
        if plan:
            attrs["amount"] = plan.price
            attrs["plan"] = plan
        elif amount is not None and amount <= 0:
            raise serializers.ValidationError("amount must be positive.")
        return attrs


class VerifyPaymentSerializer(serializers.Serializer):
    """
    Payload from frontend: plan_id, email, business_slug (slug), plus
    razorpay_order_id, razorpay_payment_id, razorpay_signature.
    """

    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()
    email = serializers.EmailField(write_only=True)
    business_slug = serializers.SlugField(write_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.all(), required=False, allow_null=True
    )

    def validate(self, attrs):
        slug = attrs["business_slug"]
        try:
            attrs["business_id"] = Business.objects.get(slug=slug)
        except Business.DoesNotExist:
            raise serializers.ValidationError(
                {"business_slug": "No business found for this slug."}
            )
        return attrs

