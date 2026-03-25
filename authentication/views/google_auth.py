import re
import secrets

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.logging import app_logger

from authentication.models import Customer
from authentication.serializers import CustomerSerializer
from authentication.tokens import create_access_token, create_refresh_token


class GoogleSignInView(APIView):
    """

    @staticmethod
    def _consent_validation_error():
        return {
            "error": "You must accept terms and privacy policy to create an account.",
            "fields": {
                "user_content_policy_accepted": "Expected 1",
                "privacy_policy_accepted": "Expected 1",
            },
        }

    @staticmethod
    def _is_accepted(value) -> bool:
        return str(value).strip() == "1"
    POST /api/auth/google/

    Sign in or sign up with Google.
    - Body: { "id_token": "<Google ID token from frontend>" }
    - Verifies the token with Google, then finds or creates a Customer.
    - Returns same shape as login: customer, access, refresh.
    """

    def post(self, request):
        id_token_str = (request.data.get("id_token") or "").strip()
        if not id_token_str:
            return Response(
                {"error": "id_token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "") or ""
        if not client_id:
            app_logger.warning("Google sign-in: GOOGLE_OAUTH_CLIENT_ID not set")
            return Response(
                {"error": "Google sign-in is not configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests
        except ImportError as e:
            app_logger.warning("Google auth package not installed", error=str(e))
            return Response(
                {
                    "error": "Google sign-in is not available",
                    "hint": "Install the google-auth package: pip install google-auth",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            id_info = google_id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                client_id,
                clock_skew_in_seconds=120,
            )
        except ValueError as e:
            err_msg = str(e)
            app_logger.warning("Google ID token verification failed", error=err_msg)
            payload = {
                "error": "Invalid or expired Google token",
                "hint": "Ensure GOOGLE_OAUTH_CLIENT_ID in .env matches the Web client ID from your Google Cloud project (same as used in the frontend).",
            }
            if getattr(settings, "DEBUG", False):
                payload["debug_message"] = err_msg
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            err_msg = str(e)
            app_logger.warning("Google ID token verification failed", error=err_msg)
            payload = {"error": "Invalid or expired Google token"}
            if getattr(settings, "DEBUG", False):
                payload["debug_message"] = err_msg
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

        google_sub = id_info.get("sub")
        email = (id_info.get("email") or "").strip()
        name = (id_info.get("name") or "").strip() or email

        if not google_sub or not email:
            return Response(
                {"error": "Google token missing email or subject"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = Customer.objects.filter(google_id=google_sub).first()
        if customer:
            access = create_access_token(customer)
            refresh = create_refresh_token(customer)
            app_logger.info(
                "Customer signed in with Google",
                email=customer.email,
                customer_id=customer.id,
            )
            return Response(
                {
                    "customer": CustomerSerializer(customer).data,
                    "access": access,
                    "refresh": refresh,
                },
            )

        existing = Customer.objects.filter(email__iexact=email).first()
        if existing:
            if existing.auth_provider == Customer.AUTH_PROVIDER_EMAIL:
                return Response(
                    {
                        "error": "An account already exists with this email. Sign in with your password.",
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            consent_terms = request.data.get("user_content_policy_accepted")
            consent_privacy = request.data.get("privacy_policy_accepted")
            if not existing.user_content_policy_accepted and self._is_accepted(consent_terms):
                existing.user_content_policy_accepted = True
            if not existing.privacy_policy_accepted and self._is_accepted(consent_privacy):
                existing.privacy_policy_accepted = True
            existing.google_id = google_sub
            existing.save(
                update_fields=[
                    "google_id",
                    "user_content_policy_accepted",
                    "privacy_policy_accepted",
                ]
            )
            access = create_access_token(existing)
            refresh = create_refresh_token(existing)
            return Response(
                {
                    "customer": CustomerSerializer(existing).data,
                    "access": access,
                    "refresh": refresh,
                },
            )

        base_username = re.sub(r"[^\w.]", "", (name or email).lower())[:100] or "user"
        username = base_username
        suffix = 0
        while Customer.objects.filter(username=username).exists():
            suffix += 1
            username = f"{base_username}{suffix}"

        consent_terms = request.data.get("user_content_policy_accepted")
        consent_privacy = request.data.get("privacy_policy_accepted")
        if not self._is_accepted(consent_terms) or not self._is_accepted(consent_privacy):
            return Response(
                self._consent_validation_error(),
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = Customer(
            email=email,
            username=username,
            password=secrets.token_hex(32),
            auth_provider=Customer.AUTH_PROVIDER_GOOGLE,
            google_id=google_sub,
            user_content_policy_accepted=True,
            privacy_policy_accepted=True,
        )
        customer.save()

        access = create_access_token(customer)
        refresh = create_refresh_token(customer)
        app_logger.info(
            "Customer signed up with Google",
            email=email,
            username=username,
            customer_id=customer.id,
        )
        return Response(
            {
                "customer": CustomerSerializer(customer).data,
                "access": access,
                "refresh": refresh,
            },
            status=status.HTTP_201_CREATED,
        )
