from rest_framework import serializers

from core.models import ClientSupportMessage, SiteEnquiry


class SiteEnquiryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteEnquiry
        fields = ("name", "email", "message")

    def validate_message(self, value: str) -> str:
        text = (value or "").strip()
        if len(text) < 3:
            raise serializers.ValidationError("Message is too short.")
        return text


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
        fields = ("id", "kind", "subject", "message", "created_at")
        read_only_fields = fields
