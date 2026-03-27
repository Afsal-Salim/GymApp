from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import TokenAuthentication

from businesses.crystal_leads import website_analytics_for_business
from businesses.models import Business


class WebsiteAnalyticsView(APIView):
    """
    GET /api/businesses/<slug>/analytics/

    Owner only. Lead events by type, WhatsApp click series, and rollups for one website.
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

        return Response(website_analytics_for_business(business))


class WebsiteAnalyticsOverviewView(APIView):
    """
    GET /api/businesses/analytics/

    Owner only. Same analytics shape as per-slug /analytics/ for every owned business.
    """

    def get(self, request):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return Response(err, status=status.HTTP_401_UNAUTHORIZED)

        businesses = Business.objects.filter(owner=customer).order_by("name")
        return Response(
            {
                "websites": [website_analytics_for_business(b) for b in businesses],
            }
        )
