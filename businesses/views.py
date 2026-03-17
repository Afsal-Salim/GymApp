from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.authentication import TokenAuthentication
from core.pagination import paginated_response

from .models import Business
from .serializers import BusinessSerializer, BusinessCreateSerializer


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
    """

    def get(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return Response(err, status=status.HTTP_401_UNAUTHORIZED)

        try:
            business = Business.objects.prefetch_related("subscriptions__plan").get(
                slug=slug
            )
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

        serializer = BusinessSerializer(business)
        return Response(serializer.data)


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

        today = timezone.now().date()
        active = (
            business.subscriptions.filter(subscription_end_date__gte=today)
            .select_related("plan")
            .order_by("-subscription_end_date")
            .first()
        )

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
