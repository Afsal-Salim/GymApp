from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import TokenAuthentication, token_auth_error_response
from core.logging import app_logger

from authentication.models import Customer
from authentication.serializers import CustomerSerializer
from authentication.tokens import create_access_token, verify_token
from core.record_status import RECORD_STATUS_ACTIVE


class MeView(APIView):
    """
    GET /api/auth/me/

    Returns the authenticated customer (same fields as login), including role (Bearer access token).
    """

    def get(self, request):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)
        return Response(CustomerSerializer(customer).data)


class RefreshView(APIView):
    """
    POST /api/auth/refresh/

    Uses a valid refresh token to issue a new access token.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

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

        raw_sub = payload.get("sub")
        if raw_sub is None:
            return Response(
                {"detail": "Invalid or expired refresh token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            customer_id = int(raw_sub)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid or expired refresh token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # No password column: refresh never checks credentials; smaller row read.
            customer = Customer.objects.only(
                "id",
                "email",
                "username",
                "role",
                "user_content_policy_accepted",
                "privacy_policy_accepted",
                "record_status",
                "created_at",
                "updated_at",
            ).get(pk=customer_id)
        except Customer.DoesNotExist:
            app_logger.error(
                "Refresh token refers to missing customer", customer_id=customer_id
            )
            return Response(
                {"detail": "Customer not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if customer.record_status != RECORD_STATUS_ACTIVE:
            return Response(
                {"detail": "Your account is not active."},
                status=status.HTTP_403_FORBIDDEN,
            )

        access = create_access_token(customer)
        app_logger.debug("Access token refreshed", customer_id=customer.id)
        return Response(
            {
                "access": access,
                "customer": CustomerSerializer(customer).data,
            }
        )
