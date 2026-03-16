import re

from rest_framework import serializers

from .models import Customer


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    username = serializers.CharField(required=False, allow_blank=True)

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

        if Customer.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Email already registered"})
        if Customer.objects.filter(username=username).exists():
            raise serializers.ValidationError({"username": "Username already taken"})

        attrs["username"] = username
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "email", "username", "created_at", "updated_at")

