from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import TokenAuthentication, token_auth_error_response
from core.phone import normalize_phone_10
from core.pagination import paginated_response
from core.record_status import RECORD_STATUS_ACTIVE

from businesses.crystal_leads import (
    lead_event_counts_by_type,
    parse_submitted_at_ms,
    whatsapp_analytics_for_business,
)
from businesses.emails import send_crystal_lead_owner_email
from businesses.models import Business, CrystalLead
from businesses.serializers import (
    MODAL_LEAD_TYPES,
    CrystalLeadModalPatchSerializer,
    CrystalLeadModalSerializer,
)
from businesses.search_filters import crystal_modal_lead_search_q
from businesses.views.owned_business import get_owned_business
from businesses.visibility import active_businesses


class CrystalLeadCreateView(APIView):
    """
    POST /api/businesses/public/<slug>/crystal-leads/

    Public, no auth. Accepts Crystal modal payloads + WhatsApp click events.
    """

    def post(self, request, slug):
        try:
            business = active_businesses().select_related("owner").get(slug=slug)
        except Business.DoesNotExist:
            return Response(
                {"detail": "No business found for this slug.", "slug": slug},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data if isinstance(request.data, dict) else {}
        lead_type = data.get("lead_type")
        valid = {c[0] for c in CrystalLead.LEAD_TYPE_CHOICES}
        if lead_type not in valid:
            return Response(
                {"detail": "Invalid or missing lead_type.", "allowed": sorted(valid)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        body_slug = (data.get("business_slug") or "").strip()
        if body_slug and body_slug != slug:
            return Response(
                {"detail": "business_slug does not match URL."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quantity = 1
        if lead_type == CrystalLead.LEAD_WHATSAPP_CLICK:
            try:
                cc = int(data.get("click_count", 1))
            except (TypeError, ValueError):
                cc = 1
            quantity = max(1, min(cc, 1000))

        payload = dict(data)
        raw_phone = payload.get("phone")
        if raw_phone is not None and str(raw_phone).strip():
            try:
                payload["phone"] = normalize_phone_10(raw_phone)
            except ValueError:
                return Response(
                    {
                        "detail": (
                            "phone must be exactly 10 digits "
                            "(optional +91 prefix or one leading 0)."
                        ),
                        "field": "phone",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        CrystalLead.objects.create(
            business=business,
            lead_type=lead_type,
            payload=payload,
            submitted_at_ms=parse_submitted_at_ms(data.get("submitted_at_ms")),
            quantity=quantity,
        )
        send_crystal_lead_owner_email(business, lead_type, payload)
        return Response({"ok": True}, status=status.HTTP_201_CREATED)


class CrystalLeadAnalyticsView(APIView):
    """
    GET /api/businesses/<slug>/crystal-leads/analytics/

    Owner only. WhatsApp click totals (day / 7d / 30d / 90d) and series by day, week, month (90d window).
    """

    def get(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        return Response(
            {
                "slug": slug,
                "whatsapp": whatsapp_analytics_for_business(business),
                "all_leads": lead_event_counts_by_type(business),
            }
        )


class CrystalLeadOwnerListView(APIView):
    """
    GET /api/businesses/<slug>/crystal-leads/

    Owner only. Lists join_now, book_free_trial, plan_visit for this business.
    Query: lead_type (optional), record_status (optional),
    search or q (optional) — case-insensitive match on payload name, email,
    message, or notes.
    """

    def get(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        qs = CrystalLead.objects.filter(
            business=business,
            lead_type__in=MODAL_LEAD_TYPES,
        ).order_by("-created_at")

        lt = (request.query_params.get("lead_type") or "").strip()
        if lt:
            if lt not in MODAL_LEAD_TYPES:
                return Response(
                    {
                        "detail": "Invalid lead_type for this list.",
                        "allowed": list(MODAL_LEAD_TYPES),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = qs.filter(lead_type=lt)

        rs = request.query_params.get("record_status")
        if rs:
            qs = qs.filter(record_status=rs)
        else:
            qs = qs.filter(record_status=RECORD_STATUS_ACTIVE)

        search = (
            request.query_params.get("search") or request.query_params.get("q") or ""
        ).strip()
        if search:
            qs = qs.filter(crystal_modal_lead_search_q(search))

        return paginated_response(request, qs, CrystalLeadModalSerializer)


class CrystalLeadOwnerDetailView(APIView):
    """
    GET, PATCH /api/businesses/<slug>/crystal-leads/<id>/

    Owner only. Single modal lead (join_now / book_free_trial / plan_visit).
    """

    def get(self, request, slug, pk):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        lead = get_object_or_404(
            CrystalLead.objects.filter(
                business=business,
                lead_type__in=MODAL_LEAD_TYPES,
            ),
            pk=pk,
        )
        return Response(CrystalLeadModalSerializer(lead).data)

    def patch(self, request, slug, pk):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        lead = get_object_or_404(
            CrystalLead.objects.filter(
                business=business,
                lead_type__in=MODAL_LEAD_TYPES,
            ),
            pk=pk,
        )
        ser = CrystalLeadModalPatchSerializer(lead, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        ser.save()
        return Response(CrystalLeadModalSerializer(lead).data)
