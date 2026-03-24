from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.logging import app_logger

from authentication.models import Customer
from authentication.tokens import create_access_token, verify_token


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
        return Response({"access": access})
