import re

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.template.loader import render_to_string

from django.conf import settings

from core.logging import app_logger

from .models import EmailOTP
from .utils import generate_otp
from .tokens import (
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    verify_token,
)
from .models import Customer
from .serializers import SignupSerializer, LoginSerializer, CustomerSerializer

class SendOTPView(APIView):
    """
    POST /api/auth/send-otp/

    Sends an OTP to the provided email for verification.
    - Validates that email is provided.
    - Generates a 6-digit OTP.
    - Stores OTP and a unique token in EmailOTP model.
    - Sends OTP to the user's email.
    - Returns a token used later for OTP verification.
    """

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
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
            html_message=html_message,
        )

        app_logger.info(
            "OTP sent to email",
            email=email,
            otp_id=otp_obj.id,
            token=str(otp_obj.token),
        )

        return Response(
            {
                "message": "OTP sent to email",
                "token": otp_obj.token
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

    def post(self, request):
        token = request.data.get("token")
        otp = request.data.get("otp")
        email = (request.data.get("email") or "").strip().lower()

        if not token or not otp:
            return Response(
                {"error": "token and otp are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Only verify signup OTPs; prefer latest for this email when email provided
        base_qs = EmailOTP.objects.filter(token=token, purpose=EmailOTP.PURPOSE_SIGNUP)
        if email:
            otp_obj = base_qs.filter(email__iexact=email).order_by("-created_at").first()
        else:
            otp_obj = base_qs.first()
        if not otp_obj:
            # Hint if token exists for password reset (wrong endpoint)
            if EmailOTP.objects.filter(token=token, purpose=EmailOTP.PURPOSE_PASSWORD_RESET).exists():
                return Response(
                    {"error": "This code is for password reset. Use POST /api/auth/verify-reset-otp/ with email, token, otp."},
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


class SignupView(APIView):
    """
    POST /api/auth/signup/

    Creates a new customer account after email verification.
    - Validates email, username, and password via SignupSerializer.
    - Ensures the email has been verified via OTP.
    - Hashes and stores password on the Customer model.
    - Returns customer data plus access and refresh tokens.
    """

    def post(self, request):
        serializer = SignupSerializer(data=request.data)

        if not serializer.is_valid():
            app_logger.warning(
                "Signup validation failed",
                errors=serializer.errors,
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        username = serializer.validated_data["username"]
        token = request.data.get("token")

        try:
            otp_obj = EmailOTP.objects.get(
                email=email,
                token=token,
                purpose=EmailOTP.PURPOSE_SIGNUP,
            )
        except EmailOTP.DoesNotExist:
            app_logger.warning(
                "Signup attempt without OTP verification",
                email=email,
                token=token,
            )
            return Response(
                {"error": "OTP verification required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not otp_obj.is_verified:
            app_logger.warning(
                "Signup blocked - email not verified",
                email=email,
                token=token,
            )
            return Response(
                {"error": "Email not verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = Customer(email=email, username=username)
        customer.set_password(password)
        customer.save()

        access = create_access_token(customer)
        refresh = create_refresh_token(customer)

        app_logger.info(
            "Customer signed up",
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


class LoginView(APIView):
    """
    POST /api/auth/login/

    Authenticates a customer using email and password.
    - On success returns customer data plus fresh access and refresh tokens.
    """
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            customer = Customer.objects.get(email=email)
        except Customer.DoesNotExist:
            app_logger.warning("Login failed: unknown email", email=email)
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not customer.check_password(password):
            app_logger.warning("Login failed: bad password", email=email)
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access = create_access_token(customer)
        refresh = create_refresh_token(customer)

        app_logger.info("Customer logged in", email=email, customer_id=customer.id)

        return Response(
            {
                "customer": CustomerSerializer(customer).data,
                "access": access,
                "refresh": refresh,
            }
        )


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
            {"message": "OTP verified. You can now set a new password.", "token": str(otp_obj.token)},
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
        # Validate password (same rules as signup)
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
        otp_obj.delete()  # one-time use
        app_logger.info("Password reset completed", email=email)
        return Response(
            {"message": "Password has been reset. You can now log in."},
            status=status.HTTP_200_OK,
        )


class RefreshView(APIView):
    """
    POST /api/auth/refresh/

    Uses a valid refresh token to issue a new access token.
    """
    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response(
                {"detail": "refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = verify_token(token, expected_type="refresh")
        if payload is None:
            app_logger.warning("Refresh token invalid or expired")
            return Response(
                {"detail": "Invalid or expired refresh token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer_id = payload.get("sub")
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            app_logger.error(
                "Refresh token refers to missing customer", customer_id=customer_id
            )
            return Response(
                {"detail": "Customer not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access = create_access_token(customer)
        app_logger.info("Access token refreshed", customer_id=customer.id)
        # Optionally rotate refresh token; here we reuse the old one until expiry.
        return Response({"access": access})
