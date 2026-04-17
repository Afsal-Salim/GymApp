from django.db.models import Prefetch, TextField
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import TokenAuthentication, token_auth_error_response
from core.pagination import paginated_response
from core.record_status import RECORD_STATUS_ACTIVE, RECORD_STATUS_INACTIVE

from businesses.models import Business
from businesses.serializers import (
    BusinessCreateSerializer,
    BusinessDetailCoreSerializer,
    BusinessListSerializer,
    BusinessPublicSerializer,
    BusinessRecordStatusSerializer,
    BusinessSerializer,
    BusinessUpdateSerializer,
)
from businesses.subscription_helpers import (
    get_active_public_subscription_for_slug,
    get_active_subscription_for_business,
    public_active_subscription_payload,
    subscription_plan_tier,
)
from businesses.views.owned_business import get_owned_business
from businesses.visibility import active_businesses
from plans.models import Plan
from subscriptions.models import Subscription
from subscriptions.trial_subscription import business_has_non_trial_subscription
from subscriptions.serializers import CurrentSubscriptionSerializer


def _owned_business_list_queryset(customer):
    """
    List queryset: Crystal JSON lives on ``BusinessWebsitePayload``; defer those
    blobs in Python while still annotating ``logo_url`` from ``logo.src`` in SQL.
    """
    logo_src = KeyTextTransform(
        "src",
        KeyTransform("logo", "website_payload__website_content"),
        output_field=TextField(),
    )
    return (
        Business.objects.filter(owner=customer, record_status=RECORD_STATUS_ACTIVE)
        .select_related("owner", "website_payload")
        .annotate(_list_logo_url=logo_src)
        .defer(
            "website_payload__website_content",
            "website_payload__website_theme",
        )
        .prefetch_related(
            Prefetch(
                "subscriptions",
                queryset=Subscription.objects.select_related("plan").order_by(
                    "-subscription_end_date"
                ),
            )
        )
        .order_by("-created_at")
    )


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

        queryset = _owned_business_list_queryset(customer)
        return paginated_response(request, queryset, BusinessListSerializer)

    def post(self, request):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        serializer = BusinessCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        business = serializer.save(owner=customer)
        refreshed = (
            Business.objects.select_related("owner", "website_payload")
            .prefetch_related(
                Prefetch(
                    "subscriptions",
                    queryset=Subscription.objects.select_related("plan").order_by(
                        "-subscription_end_date"
                    ),
                )
            )
            .get(pk=business.pk)
        )
        return Response(
            BusinessSerializer(refreshed).data,
            status=status.HTTP_201_CREATED,
        )


class BusinessDetailView(APIView):
    """
    GET /api/businesses/<slug>/
        Get a single business by slug. Only allowed if owned by the authenticated customer.
        Optional: ``?lite=1`` omits ``website_theme`` / ``website_content`` and does not
        load those columns (faster for dashboards; fetch full detail for the site builder).
    PATCH /api/businesses/<slug>/
        Partially update fields on an owned business (same slug in URL as before update,
        or use new slug after changing it — clients should follow redirects / refetch).
    """

    def get(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        lite = request.GET.get("lite", "").lower() in ("1", "true", "yes")
        business, denied = get_owned_business(
            customer,
            slug,
            with_serializer_relations=True,
            defer_website_payload=lite,
        )
        if denied:
            return denied

        serializer = (
            BusinessDetailCoreSerializer(business)
            if lite
            else BusinessSerializer(business)
        )
        return Response(serializer.data)

    def patch(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(
            customer, slug, with_serializer_relations=True
        )
        if denied:
            return denied

        serializer = BusinessUpdateSerializer(
            business, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        updated, denied = get_owned_business(
            customer, serializer.instance.slug, with_serializer_relations=True
        )
        if denied:
            return denied
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
            Business.objects.select_related("owner", "website_payload")
            .prefetch_related("subscriptions__plan")
            .get(pk=business.pk)
        )
        return Response(BusinessSerializer(updated).data, status=status.HTTP_200_OK)


class FirstRechargeEligibilityView(APIView):
    """
    GET /api/businesses/<slug>/first-recharge/

    Owner only.     ``is_first_recharge`` is true when the business has no paid (non-trial)
    subscription yet — same rule as ``POST /api/payments/create-order/`` for
    Starter first-activation vs list price. A 7-day free trial does not count.
    """

    def get(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        has_any_subscription = Subscription.objects.filter(business=business).exists()
        has_paid_subscription = business_has_non_trial_subscription(business)
        is_first = not has_paid_subscription

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
            "has_paid_subscription": has_paid_subscription,
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
            business = active_businesses().select_related("website_payload").get(slug=slug)
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
            "is_active": bool(active),
            "has_active_subscription": bool(active),
            "subscription_end_date": (
                active.subscription_end_date.isoformat() if active else None
            ),
            "plan_tier": subscription_plan_tier(active.plan) if active else None,
            "subscription": CurrentSubscriptionSerializer(active).data if active else None,
        }
        return Response(payload)


class BusinessActiveSubscriptionView(APIView):
    """
    GET /api/businesses/<slug>/active-subscription/
        Public: whether the gym has an active subscription, end date, and plan
        summary (trial / starter / pro tier, duration, price, features).
        Active = subscription_end_date >= today.
    """

    def get(self, request, slug):
        active, not_found = get_active_public_subscription_for_slug(slug)
        if not_found:
            return Response(
                {
                    "detail": "Not found.",
                    "slug": slug,
                    "is_active": False,
                    "has_active_subscription": False,
                    "subscription_end_date": None,
                    "plan_tier": None,
                    "subscription": None,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not active:
            return Response(
                {
                    "slug": slug,
                    "is_active": False,
                    "has_active_subscription": False,
                    "subscription_end_date": None,
                    "plan_tier": None,
                    "subscription": None,
                },
                status=status.HTTP_200_OK,
            )

        detail = public_active_subscription_payload(active)
        return Response(
            {
                "slug": slug,
                "is_active": True,
                "has_active_subscription": True,
                "subscription_end_date": detail["subscription_end_date"],
                "plan_tier": detail["plan_tier"],
                "subscription": detail,
            },
            status=status.HTTP_200_OK,
        )
