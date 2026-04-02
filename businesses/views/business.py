from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import TokenAuthentication, token_auth_error_response
from core.pagination import paginated_response
from core.record_status import RECORD_STATUS_ACTIVE, RECORD_STATUS_INACTIVE

from businesses.models import Business
from businesses.serializers import (
    BusinessCreateSerializer,
    BusinessPublicSerializer,
    BusinessRecordStatusSerializer,
    BusinessSerializer,
    BusinessUpdateSerializer,
)
from businesses.subscription_helpers import get_active_subscription_for_business
from businesses.views.owned_business import get_owned_business
from businesses.visibility import active_businesses
from plans.models import Plan
from subscriptions.models import Subscription
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
            return token_auth_error_response(err)

        queryset = (
            Business.objects.filter(owner=customer, record_status=RECORD_STATUS_ACTIVE)
            .prefetch_related("subscriptions__plan")
            .order_by("-created_at")
        )
        return paginated_response(request, queryset, BusinessSerializer)

    def post(self, request):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

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

    def get(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        business = (
            Business.objects.prefetch_related("subscriptions__plan")
            .get(pk=business.pk)
        )
        serializer = BusinessSerializer(business)
        return Response(serializer.data)

    def patch(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        business = (
            Business.objects.prefetch_related("subscriptions__plan")
            .get(pk=business.pk)
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


class BusinessRecordStatusView(APIView):
    """
    POST /api/businesses/<slug>/record-status/

    Owner only. Sets ``record_status`` (soft delete: ``inactive``; restore: ``active``).
    Setting ``inactive`` is rejected with 409 while the business has an active
    (non-expired, active-record) subscription.
    """

    def post(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug, require_active=False)
        if denied:
            return denied

        serializer = BusinessRecordStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data["record_status"]
        if new_status == RECORD_STATUS_INACTIVE:
            if get_active_subscription_for_business(business):
                return Response(
                    {
                        "detail": (
                            "Cannot set this website to inactive while it has an active "
                            "subscription. Cancel or wait for the subscription to end first."
                        ),
                        "code": "active_subscription_blocks_deactivate",
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        business.record_status = new_status
        business.save(update_fields=["record_status", "updated_at"])
        updated = (
            Business.objects.prefetch_related("subscriptions__plan")
            .get(pk=business.pk)
        )
        return Response(BusinessSerializer(updated).data, status=status.HTTP_200_OK)


class FirstRechargeEligibilityView(APIView):
    """
    GET /api/businesses/<slug>/first-recharge/

    Owner only. ``is_first_recharge`` is true when this business has never had a
    subscription row — same rule as ``POST /api/payments/create-order/`` for
    Starter first-activation (299) vs list price (499).
    """

    def get(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        has_any_subscription = Subscription.objects.filter(business=business).exists()
        is_first = not has_any_subscription

        starter = (
            Plan.objects.filter(
                name="Starter",
                record_status=RECORD_STATUS_ACTIVE,
                coming_soon=False,
            ).first()
        )

        payload = {
            "slug": business.slug,
            "is_first_recharge": is_first,
            "has_had_subscription": has_any_subscription,
        }

        if starter:
            list_price = str(starter.price)
            intro = (
                str(starter.first_activation_price)
                if starter.first_activation_price is not None
                else None
            )
            if is_first and starter.first_activation_price is not None:
                applicable = intro
            else:
                applicable = list_price
            payload["starter"] = {
                "plan_id": starter.id,
                "list_price": list_price,
                "first_recharge_price": intro,
                "currency": starter.currency,
                "applicable_price": applicable,
            }
        else:
            payload["starter"] = None

        return Response(payload)


class BusinessPublicBySlugView(APIView):
    """
    GET /api/businesses/public/<slug>/

    Public business details by slug. No authentication required.
    Does not expose owner email or subscription/payment data.
    """

    def get(self, request, slug):
        try:
            business = active_businesses().get(slug=slug)
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
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

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
            business = active_businesses().get(slug=slug)
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
