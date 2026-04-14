from django.conf import settings
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.logging import app_logger
from core.mail_background import send_mail_in_background

from authentication.models import EmailOTP
from authentication.utils import generate_otp


class SendOTPView(APIView):
    """
    POST /api/auth/send-otp/

    Sends an OTP to the provided email for verification.
    - Validates that email is provided.
    - Generates a 6-digit OTP.
    - Stores OTP and a unique token in EmailOTP model.
    - Sends OTP via SMTP in a background thread (response is not blocked on mail).
    - Returns a token used later for OTP verification.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            app_logger.warning(
                "OTP send attempt without email",
            )
            return Response(
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = generate_otp()

        otp_obj = EmailOTP.objects.create(
            email=email,
            otp=otp,
            purpose=EmailOTP.PURPOSE_SIGNUP,
        )

        expire_minutes = getattr(settings, "OTP_EXPIRE_MINUTES", 10)
        subject = getattr(settings, "OTP_EMAIL_SUBJECT", "Your OTP Code")
        plain_message = f"Your verification OTP is {otp}. It expires in {expire_minutes} minutes."
        html_message = render_to_string(
            "authentication/email_otp.html",
            {"otp": otp, "expire_minutes": expire_minutes, "otp_purpose": "signup"},
        )

        def _log_sent() -> None:
            app_logger.info(
                "OTP sent to email",
                email=email,
                otp_id=otp_obj.id,
                token=str(otp_obj.token),
            )

        send_mail_in_background(
            thread_name="signup_otp_email",
            on_sent=_log_sent,
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
            html_message=html_message,
        )

        return Response(
            {
                "message": "OTP sent to email",
                "token": otp_obj.token,
            },
            status=status.HTTP_200_OK,
        )


class VerifyOTPView(APIView):
    """
    POST /api/auth/verify-otp/

    Verifies the OTP sent to the user's email.
    - Validates token and OTP.
    - Checks if OTP exists and is not expired.
    - Marks the OTP as verified.
    - Allows the user to proceed with account creation.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        otp = request.data.get("otp")
        email = (request.data.get("email") or "").strip().lower()

        if not token or not otp:
            return Response(
                {"error": "token and otp are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        base_qs = EmailOTP.objects.filter(token=token, purpose=EmailOTP.PURPOSE_SIGNUP)
        if email:
            otp_obj = base_qs.filter(email__iexact=email).order_by("-created_at").first()
        else:
            otp_obj = base_qs.first()
        if not otp_obj:
            if EmailOTP.objects.filter(
                token=token, purpose=EmailOTP.PURPOSE_PASSWORD_RESET
            ).exists():
                return Response(
                    {
                        "error": "This code is for password reset. Use POST /api/auth/verify-reset-otp/ with email, token, otp.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            app_logger.warning(
                "OTP verification failed - invalid token",
                token=token,
            )
            return Response(
                {"error": "Invalid token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.is_expired():
            app_logger.warning(
                "OTP verification failed - OTP expired",
                email=otp_obj.email,
                token=str(token),
            )
            return Response(
                {"error": "OTP expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.otp != otp:
            app_logger.warning(
                "OTP verification failed - incorrect OTP",
                email=otp_obj.email,
                token=str(token),
            )
            return Response(
                {"error": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_obj.is_verified = True
        otp_obj.save()

        app_logger.info(
            "OTP verified successfully",
            email=otp_obj.email,
            token=str(token),
        )

        return Response({"message": "Email verified"})
