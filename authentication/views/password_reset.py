import re

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.logging import app_logger

from authentication.models import Customer, EmailOTP
from authentication.utils import generate_otp


class ForgotPasswordView(APIView):
    """
    POST /api/auth/forgot-password/

    Sends an OTP to the email for password reset (like signup).
    - If the account exists, creates a password_reset OTP, sends email, returns token.
    - Always returns a generic message; token only present when email was sent.
    """

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        if not email:
            return Response(
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            customer = Customer.objects.get(email__iexact=email)
        except Customer.DoesNotExist:
            app_logger.warning("Forgot password requested for unknown email", email=email)
            return Response(
                {"detail": "If that account exists, we've emailed you."},
                status=status.HTTP_200_OK,
            )

        otp = generate_otp()
        otp_obj = EmailOTP.objects.create(
            email=customer.email,
            otp=otp,
            purpose=EmailOTP.PURPOSE_PASSWORD_RESET,
        )
        expire_minutes = getattr(settings, "OTP_EXPIRE_MINUTES", 10)
        subject = getattr(
            settings,
            "OTP_PASSWORD_RESET_EMAIL_SUBJECT",
            "Your password reset code",
        )
        plain_message = f"Your password reset OTP is {otp}. It expires in {expire_minutes} minutes."
        html_message = render_to_string(
            "authentication/email_otp.html",
            {"otp": otp, "expire_minutes": expire_minutes, "otp_purpose": "password_reset"},
        )
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            fail_silently=False,
            html_message=html_message,
        )
        app_logger.info(
            "Password reset OTP sent",
            email=email,
            otp_id=otp_obj.id,
        )
        return Response(
            {
                "detail": "If that account exists, we've emailed you.",
                "token": otp_obj.token,
                "expires_in_minutes": expire_minutes,
            },
            status=status.HTTP_200_OK,
        )


class VerifyResetOTPView(APIView):
    """
    POST /api/auth/verify-reset-otp/

    Verifies the OTP sent for password reset. Use the token from forgot-password.
    Body: email, token, otp. On success, OTP is marked verified; then call reset-password.
    """

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        token = request.data.get("token")
        otp = request.data.get("otp")
        if not email or not token or not otp:
            return Response(
                {"error": "email, token and otp are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        otp_obj = (
            EmailOTP.objects.filter(
                email__iexact=email,
                token=token,
                purpose=EmailOTP.PURPOSE_PASSWORD_RESET,
            )
            .order_by("-created_at")
            .first()
        )
        if not otp_obj:
            return Response(
                {"error": "Invalid or expired link. Request a new code."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if otp_obj.is_expired():
            return Response(
                {"error": "OTP expired. Request a new code."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if otp_obj.otp != otp:
            return Response(
                {"error": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        otp_obj.is_verified = True
        otp_obj.save()
        app_logger.info("Password reset OTP verified", email=email)
        return Response(
            {
                "message": "OTP verified. You can now set a new password.",
                "token": str(otp_obj.token),
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """
    POST /api/auth/reset-password/

    Sets a new password after OTP verification. Body: email, token (from forgot-password), new_password.
    The OTP for this token must have been verified via verify-reset-otp first.
    """

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        token = request.data.get("token")
        new_password = request.data.get("new_password")
        if not email or not token:
            return Response(
                {"error": "email and token are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not new_password:
            return Response(
                {"error": "new_password is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        otp_obj = (
            EmailOTP.objects.filter(
                email__iexact=email,
                token=token,
                purpose=EmailOTP.PURPOSE_PASSWORD_RESET,
                is_verified=True,
            )
            .order_by("-created_at")
            .first()
        )
        if not otp_obj:
            return Response(
                {"error": "Invalid or expired. Verify the OTP first, then set password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            customer = Customer.objects.get(email__iexact=email)
        except Customer.DoesNotExist:
            return Response(
                {"error": "Account not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (8 <= len(new_password) <= 30):
            return Response(
                {"error": "Password must be between 8 and 30 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.search(r"[A-Z]", new_password) or not re.search(r"\d", new_password):
            return Response(
                {"error": "Password must contain at least one uppercase letter and one number."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        customer.set_password(new_password)
        customer.save()
        otp_obj.delete()
        app_logger.info("Password reset completed", email=email)
        return Response(
            {"message": "Password has been reset. You can now log in."},
            status=status.HTTP_200_OK,
        )
