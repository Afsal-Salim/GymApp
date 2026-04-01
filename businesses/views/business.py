from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import TokenAuthentication
from core.pagination import paginated_response

from businesses.models import Business
from businesses.serializers import (
    BusinessCreateSerializer,
    BusinessPublicSerializer,
    BusinessSerializer,
    BusinessUpdateSerializer,
)
from businesses.subscription_helpers import get_active_subscription_for_business
from subscriptions.serializers import CurrentSubscriptionSerializer


class BusinessListCreateView(APIView):
    """
    GET  /api/businesses/
        List all businesses owned by the authenticated customer.
    POST /api/businesses/
        Create a new business (owner = authenticated customer).
    """

    def get(self, request):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return Response(err, status=status.HTTP_401_UNAUTHORIZED)

        queryset = (
            Business.objects.filter(owner=customer)
            .prefetch_related("subscriptions__plan")
            .order_by("-created_at")
        )
        return paginated_response(request, queryset, BusinessSerializer)

    def post(self, request):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return Response(err, status=status.HTTP_401_UNAUTHORIZED)

        serializer = BusinessCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        business = serializer.save(owner=customer)
        return Response(
            BusinessSerializer(business).data,
            status=status.HTTP_201_CREATED,
        )


class BusinessDetailView(APIView):
    """
    GET /api/businesses/<slug>/
        Get a single business by slug. Only allowed if owned by the authenticated customer.
    PATCH /api/businesses/<slug>/
        Partially update fields on an owned business (same slug in URL as before update,
        or use new slug after changing it — clients should follow redirects / refetch).
    """

    def _owned_business(self, customer, slug):
        try:
            business = Business.objects.prefetch_related("subscriptions__plan").get(
                slug=slug
            )
        except Business.DoesNotExist:
            return None
        if business.owner_id != customer.id:
            return None
        return business

    def get(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return Response(err, status=status.HTTP_401_UNAUTHORIZED)

        business = self._owned_business(customer, slug)
        if business is None:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BusinessSerializer(business)
        return Response(serializer.data)

    def patch(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return Response(err, status=status.HTTP_401_UNAUTHORIZED)

        business = self._owned_business(customer, slug)
        if business is None:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BusinessUpdateSerializer(
            business, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        updated = (
            Business.objects.prefetch_related("subscriptions__plan")
            .get(pk=serializer.instance.pk)
        )
        return Response(BusinessSerializer(updated).data, status=status.HTTP_200_OK)


class BusinessPublicBySlugView(APIView):
    """
    GET /api/businesses/public/<slug>/

    Public business details by slug. No authentication required.
    Does not expose owner email or subscription/payment data.
    """

    def get(self, request, slug):
        try:
            business = Business.objects.get(slug=slug)
        except Business.DoesNotExist:
            return Response(
                {"detail": "No business found for this slug.", "slug": slug},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(BusinessPublicSerializer(business).data)


class CurrentSubscriptionDetailView(APIView):
    """
    GET /api/businesses/<slug>/subscription/

    Owner only. Current active subscription with full plan (price, duration, features).
    """

    def get(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return Response(err, status=status.HTTP_401_UNAUTHORIZED)

        try:
            business = Business.objects.get(slug=slug)
        except Business.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if business.owner_id != customer.id:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        active = get_active_subscription_for_business(business)
        payload = {
            "business": {"slug": business.slug, "name": business.name},
            "has_active_subscription": bool(active),
            "subscription": CurrentSubscriptionSerializer(active).data if active else None,
        }
        return Response(payload)


class BusinessActiveSubscriptionView(APIView):
    """
    GET /api/businesses/<slug>/active-subscription/
        Check if the business has a valid (active) subscription.
        No auth required – for public pages to validate subscription.
        Active = subscription_end_date >= today.
    """

    def get(self, request, slug):
        try:
            business = Business.objects.get(slug=slug)
        except Business.DoesNotExist:
            return Response(
                {"detail": "Not found.", "slug": slug, "has_active_subscription": False},
                status=status.HTTP_404_NOT_FOUND,
            )

        active = get_active_subscription_for_business(business)

        if not active:
            return Response(
                {
                    "slug": slug,
                    "has_active_subscription": False,
                    "subscription": None,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "slug": slug,
                "has_active_subscription": True,
                "subscription": {
                    "id": active.id,
                    "plan_name": active.plan.name,
                    "subscription_start_date": active.subscription_start_date.isoformat(),
                    "subscription_end_date": active.subscription_end_date.isoformat(),
                },
            },
            status=status.HTTP_200_OK,
        )
