from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import TokenAuthentication

from businesses.crystal_leads import (
    lead_event_counts_by_type,
    parse_submitted_at_ms,
    whatsapp_analytics_for_business,
)
from businesses.emails import send_crystal_lead_owner_email
from businesses.models import Business, CrystalLead


class CrystalLeadCreateView(APIView):
    """
    POST /api/businesses/public/<slug>/crystal-leads/

    Public, no auth. Accepts Crystal modal payloads + WhatsApp click events.
    """

    def post(self, request, slug):
        try:
            business = Business.objects.select_related("owner").get(slug=slug)
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

        CrystalLead.objects.create(
            business=business,
            lead_type=lead_type,
            payload=dict(data),
            submitted_at_ms=parse_submitted_at_ms(data.get("submitted_at_ms")),
            quantity=quantity,
        )
        send_crystal_lead_owner_email(business, lead_type, dict(data))
        return Response({"ok": True}, status=status.HTTP_201_CREATED)


class CrystalLeadAnalyticsView(APIView):
    """
    GET /api/businesses/<slug>/crystal-leads/analytics/

    Owner only. WhatsApp click totals (day / 7d / 30d / 90d) and series by day, week, month (90d window).
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

        return Response(
            {
                "slug": slug,
                "whatsapp": whatsapp_analytics_for_business(business),
                "all_leads": lead_event_counts_by_type(business),
            }
        )
