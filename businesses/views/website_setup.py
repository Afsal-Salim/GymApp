from django.db.models import Prefetch
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import TokenAuthentication, token_auth_error_response

from businesses.models import Business
from businesses.serializers import BusinessSerializer, CrystalWebsiteSetupSerializer
from subscriptions.models import Subscription


class CrystalWebsiteSetupView(APIView):
    """
    POST /api/businesses/website-setup/

    Authenticated. Creates a new business from Crystal website builder payload
    (slug, theme, content). Derives name, description, phone, address, and
    location_map_url from content (e.g. content.contacts.items and locationMapUrl).
    """

    def post(self, request):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        serializer = CrystalWebsiteSetupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        name, description = serializer.derive_name_and_description()
        phone, address, location_map_url = serializer.derive_contact_and_location()

        business = Business.objects.create(
            owner=customer,
            name=name,
            slug=serializer.validated_data["slug"],
            description=description,
            phone=phone,
            address=address,
            location_map_url=location_map_url,
        )
        payload = business.website_payload
        payload.website_theme = serializer.validated_data["theme"]
        payload.website_content = serializer.validated_data["content"]
        payload.save(update_fields=["website_theme", "website_content", "updated_at"])

        business = (
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
            BusinessSerializer(business).data,
            status=status.HTTP_201_CREATED,
        )
