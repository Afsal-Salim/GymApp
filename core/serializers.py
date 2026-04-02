from rest_framework import serializers

from core.models import ClientSupportMessage, SiteEnquiry


class SiteEnquiryCreateSerializer(serializers.ModelSerializer):
    """General home page contact form (``/api/public/enquiries/``)."""

    class Meta:
        model = SiteEnquiry
        fields = ("name", "email", "message")

    def validate_message(self, value: str) -> str:
        text = (value or "").strip()
        if len(text) < 3:
            raise serializers.ValidationError("Message is too short.")
        return text

    def create(self, validated_data):
        validated_data["enquiry_kind"] = SiteEnquiry.KIND_GENERAL
        return super().create(validated_data)


class ServiceEnquiryCreateSerializer(serializers.ModelSerializer):
    """Home page service enquiry (``/api/public/service-enquiries/``)."""

    class Meta:
        model = SiteEnquiry
        fields = ("name", "email", "phone", "message", "service_topic")

    def validate_message(self, value: str) -> str:
        text = (value or "").strip()
        if len(text) < 3:
            raise serializers.ValidationError("Message is too short.")
        return text

    def validate_phone(self, value: str) -> str:
        text = (value or "").strip()
        if len(text) < 5:
            raise serializers.ValidationError(
                "Enter a valid phone number (at least 5 characters)."
            )
        return text[:50]

    def validate_service_topic(self, value: str) -> str:
        return (value or "").strip()[:255]

    def create(self, validated_data):
        validated_data["enquiry_kind"] = SiteEnquiry.KIND_SERVICE
        return super().create(validated_data)


class ClientSupportMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientSupportMessage
        fields = ("kind", "subject", "message")

    def validate_message(self, value: str) -> str:
        text = (value or "").strip()
        if len(text) < 3:
            raise serializers.ValidationError("Message is too short.")
        return text

    def validate_subject(self, value: str) -> str:
        return (value or "").strip()[:200]


class ClientSupportMessageListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientSupportMessage
        fields = (
            "id",
            "kind",
            "subject",
            "message",
            "support_status",
            "feedback_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
