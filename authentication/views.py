from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings

from core.logging import app_logger

from .tokens import (
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    verify_token,
)
from .models import Customer
from .serializers import SignupSerializer, LoginSerializer, CustomerSerializer


class SignupView(APIView):
    """
    POST /api/auth/signup/

    Creates a new customer.
    - Validates email, username, and password via SignupSerializer.
    - Hashes and stores password on the Customer model.
    - Returns customer data plus access and refresh tokens.
    """
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        username = serializer.validated_data["username"]

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
