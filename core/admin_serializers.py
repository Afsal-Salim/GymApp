from rest_framework import serializers

from authentication.models import Customer
from businesses.models import Business
from core.models import ClientSupportMessage, SiteEnquiry


class AdminSiteEnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteEnquiry
        fields = (
            "id",
            "name",
            "email",
            "phone",
            "service_topic",
            "message",
            "enquiry_kind",
            "enquiry_status",
            "record_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class AdminSiteEnquiryPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteEnquiry
        fields = ("enquiry_status", "record_status")


class AdminCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = (
            "id",
            "username",
            "email",
            "auth_provider",
            "role",
            "record_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminCustomerPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("record_status",)


class AdminBusinessSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    owner_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Business
        fields = (
            "id",
            "owner_id",
            "owner_email",
            "name",
            "slug",
            "record_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminBusinessPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ("record_status",)


class AdminClientSupportSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    customer_username = serializers.CharField(source="customer.username", read_only=True)
    customer_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClientSupportMessage
        fields = (
            "id",
            "customer_id",
            "customer_email",
            "customer_username",
            "kind",
            "subject",
            "message",
            "support_status",
            "feedback_status",
            "record_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminClientSupportPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientSupportMessage
        fields = ("support_status", "feedback_status", "record_status")

    def validate(self, attrs):
        kind = self.instance.kind if self.instance else None
        if kind == ClientSupportMessage.KIND_SUPPORT:
            if "feedback_status" in attrs and attrs["feedback_status"] is not None:
                raise serializers.ValidationError(
                    {"feedback_status": "Not applicable for support tickets."}
                )
        elif kind == ClientSupportMessage.KIND_FEEDBACK:
            if "support_status" in attrs and attrs["support_status"] is not None:
                raise serializers.ValidationError(
                    {"support_status": "Not applicable for feedback."}
                )
        return attrs
