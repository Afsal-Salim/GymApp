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


def _google_signin_consent_is_accepted(value) -> bool:
    """True if client sent 1 or '1' for a policy flag."""
    return str(value).strip() == "1"


def _google_signin_consent_error_body() -> dict:
    return {
        "error": "You must accept terms and privacy policy to create an account.",
        "fields": {
            "user_content_policy_accepted": "Expected 1",
            "privacy_policy_accepted": "Expected 1",
        },
    }


def _google_auth_flow(step: str, **extra) -> None:
    """Trace POST /api/auth/google/ — never log id_token contents."""
    app_logger.info("google_auth_flow", step=step, **extra)


class GoogleSignInView(APIView):
    """
    POST /api/auth/google/

    Sign in or sign up with Google.
    - Body: id_token, user_content_policy_accepted, privacy_policy_accepted (1 for new signups)
    - Verifies the token with Google, then finds or creates a Customer.
    - Returns same shape as login: customer, access, refresh.

    Module-level helpers are canonical; the static methods below delegate to them so
    ``self._is_accepted`` / ``self._consent_validation_error`` never break if used again.
    """

    @staticmethod
    def _is_accepted(value) -> bool:
        return _google_signin_consent_is_accepted(value)

    @staticmethod
    def _consent_validation_error() -> dict:
        return _google_signin_consent_error_body()

    def post(self, request):
        last_step = "post_enter"
        _google_auth_flow(last_step)

        try:
            last_step = "read_id_token"
            _google_auth_flow(last_step)
            id_token_str = (request.data.get("id_token") or "").strip()
            if not id_token_str:
                _google_auth_flow("exit_400_no_id_token")
                return Response(
                    {"error": "id_token is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            _google_auth_flow(
                "id_token_present",
                id_token_chars=len(id_token_str),
            )

            last_step = "read_google_oauth_client_id"
            _google_auth_flow(last_step)
            client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "") or ""
            if not client_id:
                app_logger.warning("Google sign-in: GOOGLE_OAUTH_CLIENT_ID not set")
                _google_auth_flow("exit_503_no_client_id")
                return Response(
                    {"error": "Google sign-in is not configured"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            last_step = "import_google_auth_libs"
            _google_auth_flow(last_step)
            try:
                from google.oauth2 import id_token as google_id_token
                from google.auth.transport import requests as google_requests
            except ImportError as e:
                app_logger.warning("Google auth package not installed", error=str(e))
                _google_auth_flow("exit_503_import_error")
                return Response(
                    {
                        "error": "Google sign-in is not available",
                        "hint": "Install the google-auth package: pip install google-auth",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            last_step = "before_verify_oauth2_token"
            _google_auth_flow(last_step)
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
                _google_auth_flow("exit_400_verify_value_error")
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
                _google_auth_flow("exit_400_verify_other")
                payload = {"error": "Invalid or expired Google token"}
                if getattr(settings, "DEBUG", False):
                    payload["debug_message"] = err_msg
                return Response(payload, status=status.HTTP_400_BAD_REQUEST)

            last_step = "after_verify_oauth2_token"
            _google_auth_flow(last_step)
            google_sub = id_info.get("sub")
            email = (id_info.get("email") or "").strip()
            name = (id_info.get("name") or "").strip() or email

            last_step = "validate_claims_sub_email"
            _google_auth_flow(last_step, has_sub=bool(google_sub), has_email=bool(email))
            if not google_sub or not email:
                _google_auth_flow("exit_400_missing_sub_or_email")
                return Response(
                    {"error": "Google token missing email or subject"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            last_step = "lookup_customer_by_google_id"
            _google_auth_flow(last_step)
            customer = Customer.objects.filter(google_id=google_sub).first()
            if customer:
                last_step = "branch_existing_google_user_create_tokens"
                _google_auth_flow(last_step, customer_id=customer.id)
                access = create_access_token(customer)
                refresh = create_refresh_token(customer)
                app_logger.info(
                    "Customer signed in with Google",
                    email=customer.email,
                    customer_id=customer.id,
                )
                _google_auth_flow("exit_200_existing_google")
                return Response(
                    {
                        "customer": CustomerSerializer(customer).data,
                        "access": access,
                        "refresh": refresh,
                    },
                )

            last_step = "lookup_customer_by_email"
            _google_auth_flow(last_step)
            existing = Customer.objects.filter(email__iexact=email).first()
            if existing:
                last_step = "branch_existing_email_check_provider"
                _google_auth_flow(last_step, customer_id=existing.id)
                if existing.auth_provider == Customer.AUTH_PROVIDER_EMAIL:
                    _google_auth_flow("exit_409_email_password_account")
                    return Response(
                        {
                            "error": "An account already exists with this email. Sign in with your password.",
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
                last_step = "branch_link_google_to_existing"
                _google_auth_flow(last_step)
                consent_terms = request.data.get("user_content_policy_accepted")
                consent_privacy = request.data.get("privacy_policy_accepted")
                if not existing.user_content_policy_accepted and _google_signin_consent_is_accepted(
                    consent_terms
                ):
                    existing.user_content_policy_accepted = True
                if not existing.privacy_policy_accepted and _google_signin_consent_is_accepted(
                    consent_privacy
                ):
                    existing.privacy_policy_accepted = True
                existing.google_id = google_sub
                last_step = "save_existing_customer_link_google"
                _google_auth_flow(last_step)
                existing.save(
                    update_fields=[
                        "google_id",
                        "user_content_policy_accepted",
                        "privacy_policy_accepted",
                    ]
                )
                last_step = "create_tokens_linked_account"
                _google_auth_flow(last_step)
                access = create_access_token(existing)
                refresh = create_refresh_token(existing)
                _google_auth_flow("exit_200_linked_google")
                return Response(
                    {
                        "customer": CustomerSerializer(existing).data,
                        "access": access,
                        "refresh": refresh,
                    },
                )

            last_step = "new_user_build_username"
            _google_auth_flow(last_step)
            base_username = re.sub(r"[^\w.]", "", (name or email).lower())[:100] or "user"
            username = base_username
            suffix = 0
            while Customer.objects.filter(username=username).exists():
                suffix += 1
                username = f"{base_username}{suffix}"

            last_step = "new_user_check_consent_flags"
            _google_auth_flow(last_step)
            consent_terms = request.data.get("user_content_policy_accepted")
            consent_privacy = request.data.get("privacy_policy_accepted")
            if not _google_signin_consent_is_accepted(
                consent_terms
            ) or not _google_signin_consent_is_accepted(consent_privacy):
                _google_auth_flow("exit_400_consent_required")
                return Response(
                    _google_signin_consent_error_body(),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            last_step = "new_user_instantiate_customer"
            _google_auth_flow(last_step)
            customer = Customer(
                email=email,
                username=username,
                password=secrets.token_hex(32),
                auth_provider=Customer.AUTH_PROVIDER_GOOGLE,
                google_id=google_sub,
                user_content_policy_accepted=True,
                privacy_policy_accepted=True,
            )
            last_step = "new_user_save_customer"
            _google_auth_flow(last_step)
            customer.save()

            last_step = "new_user_create_tokens"
            _google_auth_flow(last_step)
            access = create_access_token(customer)
            refresh = create_refresh_token(customer)
            app_logger.info(
                "Customer signed up with Google",
                email=email,
                username=username,
                customer_id=customer.id,
            )
            _google_auth_flow("exit_201_new_google_signup")
            return Response(
                {
                    "customer": CustomerSerializer(customer).data,
                    "access": access,
                    "refresh": refresh,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception:
            app_logger.exception(
                "google_auth_flow unhandled exception",
                last_step=last_step,
            )
            raise
