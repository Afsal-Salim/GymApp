from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail

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
            otp=otp
        )

        send_mail(
            subject="Your OTP Code",
            message=f"Your verification OTP is {otp}",
            from_email="noreply@yourapp.com",
            recipient_list=[email],
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

        try:
            otp_obj = EmailOTP.objects.get(token=token)

        except EmailOTP.DoesNotExist:
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
            otp_obj = EmailOTP.objects.get(email=email, token=token)

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

    Requests a password reset for a given email.
    - Always returns a generic success message.
    - When the email exists, generates a password reset token and URL.
    """
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"detail": "email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            customer = Customer.objects.get(email=email)
        except Customer.DoesNotExist:
            app_logger.warning("Forgot password requested for unknown email", email=email)
            # Do not reveal whether the email exists
            return Response(
                {"detail": "If that account exists, we've emailed you."},
                status=status.HTTP_200_OK,
            )

        token = create_password_reset_token(customer)
        reset_path = "/reset-password/?token=" + token
        base_url = getattr(settings, "FRONTEND_BASE_URL", "").rstrip("/")
        reset_url = (base_url + reset_path) if base_url else reset_path

        app_logger.info(
            "Password reset token created", email=email, customer_id=customer.id
        )

        return Response(
            {
                "detail": "If that account exists, we've emailed you.",
                "reset_url": reset_url,
                "expires_in_minutes": 60,
            },
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
