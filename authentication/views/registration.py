from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.logging import app_logger

from authentication.models import Customer, EmailOTP
from authentication.serializers import (
    CustomerSerializer,
    LoginSerializer,
    SignupSerializer,
)
from authentication.tokens import create_access_token, create_refresh_token
from core.email_notifications import notify_new_potential_client
from core.record_status import RECORD_STATUS_ACTIVE


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
        user_content_policy_accepted = (
            serializer.validated_data["user_content_policy_accepted"] == 1
        )
        privacy_policy_accepted = serializer.validated_data["privacy_policy_accepted"] == 1
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

        customer = Customer(
            email=email,
            username=username,
            user_content_policy_accepted=user_content_policy_accepted,
            privacy_policy_accepted=privacy_policy_accepted,
        )
        customer.set_password(password)
        customer.save()

        notify_new_potential_client(
            email=customer.email,
            username=customer.username,
            customer_id=customer.id,
            source="email_signup",
        )

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

        if customer.record_status != RECORD_STATUS_ACTIVE:
            return Response(
                {"detail": "Your account is not active."},
                status=status.HTTP_403_FORBIDDEN,
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
