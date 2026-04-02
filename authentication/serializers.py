import re

from rest_framework import serializers

from .models import Customer


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    username = serializers.CharField(required=False, allow_blank=True)
    user_content_policy_accepted = serializers.IntegerField()
    privacy_policy_accepted = serializers.IntegerField()

    def validate_password(self, value: str) -> str:
        if not (8 <= len(value) <= 30):
            raise serializers.ValidationError(
                "Password must be between 8 and 30 characters long."
            )
        if not re.search(r"[A-Z]", value) or not re.search(r"\d", value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter and one number."
            )
        return value

    def validate(self, attrs):
        email = attrs["email"]
        username = attrs.get("username") or email
        user_content_policy_accepted = attrs.get("user_content_policy_accepted")
        privacy_policy_accepted = attrs.get("privacy_policy_accepted")

        if Customer.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Email already registered"})
        if Customer.objects.filter(username=username).exists():
            raise serializers.ValidationError({"username": "Username already taken"})
        if user_content_policy_accepted != 1:
            raise serializers.ValidationError(
                {
                    "user_content_policy_accepted": "You must accept the terms to create an account."
                }
            )
        if privacy_policy_accepted != 1:
            raise serializers.ValidationError(
                {
                    "privacy_policy_accepted": "You must accept the privacy policy to create an account."
                }
            )

        attrs["username"] = username
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = (
            "id",
            "email",
            "username",
            "role",
            "user_content_policy_accepted",
            "privacy_policy_accepted",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("role",)

