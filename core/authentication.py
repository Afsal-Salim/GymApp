from typing import Optional, Tuple

from django.http import HttpRequest

from authentication.models import Customer
from authentication.tokens import verify_token


class TokenAuthentication:
    """
    Reusable token authentication helper.

    Expects an Authorization header of the form:
        Authorization: Bearer <access_token>

    Usage in any view:

        from core.authentication import TokenAuthentication

        def my_view(request):
            customer, error = TokenAuthentication().authenticate(request)
            if error:
                return JsonResponse(error, status=401)
            ...
    """

    header_name = "HTTP_AUTHORIZATION"
    keyword = "Bearer"

    def get_header(self, request: HttpRequest) -> str:
        return request.META.get(self.header_name, "")

    def get_token(self, header: str) -> Optional[str]:
        if not header:
            return None
        parts = header.split()
        if len(parts) == 2 and parts[0] == self.keyword:
            return parts[1]
        return None

    def authenticate(self, request: HttpRequest) -> Tuple[Optional[Customer], Optional[dict]]:
        header = self.get_header(request)
        token = self.get_token(header)
        if not token:
            return None, {"detail": "Authorization header missing or invalid"}

        payload = verify_token(token, expected_type="access")
        if payload is None:
            return None, {"detail": "Invalid or expired access token"}

        customer_id = payload.get("sub")
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return None, {"detail": "Customer not found"}

        return customer, None

