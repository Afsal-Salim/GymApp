from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import TokenAuthentication

from businesses.crystal_leads import (
    resolve_analytics_preset,
    website_analytics_for_business,
)
from businesses.models import Business


class WebsiteAnalyticsView(APIView):
    """
    GET /api/businesses/<slug>/analytics/

    Owner only. Lead events by type, WhatsApp click series, and rollups for one website.

    Query: ``range`` — one of ``1d``, ``3d``, ``5d``, ``10d``, ``1m``, ``3m`` (default ``10d``).
    Drives ``line_graph`` (hourly buckets for ``1d``, else daily), ``totals_in_range``,
    and ``leads_by_type_in_range``.
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

        preset, allowed = resolve_analytics_preset(request.query_params.get("range"))
        if preset is None:
            return Response(
                {
                    "detail": "Invalid range. Use one of the allowed_presets values.",
                    "allowed_presets": allowed,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(website_analytics_for_business(business, range_preset=preset))


class WebsiteAnalyticsOverviewView(APIView):
    """
    GET /api/businesses/analytics/

    Owner only. Same analytics shape as per-slug /analytics/ for every owned business.

    Query: ``range`` — same presets as ``/api/businesses/<slug>/analytics/``.
    """

    def get(self, request):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return Response(err, status=status.HTTP_401_UNAUTHORIZED)

        preset, allowed = resolve_analytics_preset(request.query_params.get("range"))
        if preset is None:
            return Response(
                {
                    "detail": "Invalid range. Use one of the allowed_presets values.",
                    "allowed_presets": allowed,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        businesses = Business.objects.filter(owner=customer).order_by("name")
        return Response(
            {
                "range_applied": preset,
                "websites": [
                    website_analytics_for_business(b, range_preset=preset)
                    for b in businesses
                ],
            }
        )
