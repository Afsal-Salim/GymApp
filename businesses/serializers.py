from rest_framework import serializers

from subscriptions.models import Subscription

from .models import Business


class SubscriptionListSerializer(serializers.ModelSerializer):
    """Minimal subscription info for embedding in business list."""

    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "plan",
            "plan_name",
            "payment_id",
            "subscription_start_date",
            "subscription_end_date",
        )


class BusinessSerializer(serializers.ModelSerializer):
    """Full read serializer (includes owner id, email, username, subscriptions)."""

    owner_email = serializers.SerializerMethodField()
    owner_username = serializers.SerializerMethodField()
    subscriptions = SubscriptionListSerializer(many=True, read_only=True)

    class Meta:
        model = Business
        fields = (
            "id",
            "owner",
            "owner_email",
            "owner_username",
            "name",
            "slug",
            "description",
            "phone",
            "address",
            "location_map_url",
            "website_theme",
            "website_content",
            "subscriptions",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner", "created_at", "updated_at")

    def get_owner_email(self, obj):
        return obj.owner.email if obj.owner_id else None

    def get_owner_username(self, obj):
        return obj.owner.username if obj.owner_id else None


class BusinessPublicSerializer(serializers.ModelSerializer):
    """
    Public business profile (no owner identifiers). For gym pages / shareable links by slug.
    """

    class Meta:
        model = Business
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "phone",
            "address",
            "location_map_url",
            "website_theme",
            "website_content",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class BusinessCreateSerializer(serializers.ModelSerializer):
    """For creating a business; owner is set in the view."""

    class Meta:
        model = Business
        fields = ("name", "slug", "description", "phone", "address", "location_map_url")

    def validate_slug(self, value):
        if Business.objects.filter(slug=value).exists():
            raise serializers.ValidationError("A business with this slug already exists.")
        return value


def _text_from_description_lead(lead) -> str:
    if not isinstance(lead, dict):
        return ""
    parts = [lead.get("before"), lead.get("accent"), lead.get("after")]
    return " ".join(str(p) for p in parts if p).strip()


class CrystalWebsiteSetupSerializer(serializers.Serializer):
    """
    POST /api/businesses/website-setup/ — Crystal builder draft (slug + theme + content).
    Creates a new Business for the authenticated owner.

    Populates Business.phone, address, location_map_url from content.contacts when present:
    - contacts.locationMapUrl (or location_map_url) → location_map_url
    - contacts.items[] with id "phone" → phone (value or tel: href)
    - contacts.items[] with id "address" → address
    """

    slug = serializers.SlugField(max_length=255)
    theme = serializers.JSONField()
    content = serializers.JSONField()

    def validate_slug(self, value):
        if Business.objects.filter(slug=value).exists():
            raise serializers.ValidationError("A business with this slug already exists.")
        return value

    def validate_theme(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("theme must be a JSON object.")
        return value

    def validate_content(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("content must be a JSON object.")
        return value

    def derive_name_and_description(self) -> tuple[str, str]:
        content = self.validated_data.get("content") or {}
        header = content.get("header") if isinstance(content.get("header"), dict) else {}
        title = header.get("title")
        name = (str(title).strip() if title else "") or self.validated_data[
            "slug"
        ].replace("-", " ").title()
        name = name[:255]

        desc = ""
        desc_block = content.get("description") if isinstance(content.get("description"), dict) else {}
        if isinstance(desc_block, dict):
            body = desc_block.get("body")
            if isinstance(body, str) and body.strip():
                desc = body.strip()[:5000]
            if not desc:
                desc = _text_from_description_lead(desc_block.get("lead"))[:5000]

        return name, desc

    def derive_contact_and_location(self) -> tuple[str, str, str]:
        """
        From content.contacts: locationMapUrl, and items with id phone / address.
        Full content (including contacts) is still stored in website_content.
        """
        content = self.validated_data.get("content") or {}
        contacts = content.get("contacts") if isinstance(content.get("contacts"), dict) else {}

        location_map_url = ""
        for key in ("locationMapUrl", "location_map_url"):
            raw = contacts.get(key)
            if isinstance(raw, str) and raw.strip():
                location_map_url = raw.strip()[:2000]
                break

        phone = ""
        address = ""
        items = contacts.get("items")
        if isinstance(items, list):
            for it in items:
                if not isinstance(it, dict):
                    continue
                item_id = str(it.get("id") or "").lower()
                if item_id == "phone":
                    val = str(it.get("value") or "").strip()
                    href = str(it.get("href") or "").strip()
                    if val:
                        phone = val[:50]
                    elif href.lower().startswith("tel:"):
                        phone = href[4:].strip()[:50]
                elif item_id == "address":
                    val = str(it.get("value") or "").strip()
                    if val:
                        address = val[:5000]

        return phone, address, location_map_url

