from rest_framework import serializers

from core.phone import normalize_phone_10, normalize_phone_10_or_empty
from core.s3_gym_images import gym_image_browser_url
from core.record_status import RECORD_STATUS_CHOICES
from subscriptions.models import Subscription

from .models import Business, BusinessEnquiry, BusinessWebsitePayload, CrystalLead


def _website_content_dict(business) -> dict:
    p = getattr(business, "website_payload", None)
    if p is None:
        return {}
    wc = p.website_content
    return wc if isinstance(wc, dict) else {}


def business_logo_dict(business) -> dict:
    """
    Unified logo payload for list/detail/public APIs.

    - ``type`` ``"s3"``: owner uploaded via POST …/logo/; ``url`` is browser-safe (presigned when configured).
    - ``type`` ``"url"``: external or builder URL from ``website_content.logo.src`` (no S3 key).
    - ``type`` ``null``: no logo configured.
    """
    key = (getattr(business, "logo_s3_key", None) or "").strip()
    if key:
        url = gym_image_browser_url(key) or ""
        return {"type": "s3", "url": url, "s3_key": key}
    wc = _website_content_dict(business)
    logo = wc.get("logo") if isinstance(wc.get("logo"), dict) else {}
    src = (logo.get("src") or "").strip() if isinstance(logo, dict) else ""
    if src:
        return {"type": "url", "url": src, "s3_key": None}
    return {"type": None, "url": "", "s3_key": None}


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
    logo = serializers.SerializerMethodField()
    website_theme = serializers.SerializerMethodField()
    website_content = serializers.SerializerMethodField()

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
            "logo",
            "website_theme",
            "website_content",
            "subscriptions",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner", "created_at", "updated_at")

    def get_website_theme(self, obj):
        p = getattr(obj, "website_payload", None)
        if p is None:
            return {}
        wt = p.website_theme
        return wt if isinstance(wt, dict) else {}

    def get_website_content(self, obj):
        return _website_content_dict(obj)

    def get_logo(self, obj):
        return business_logo_dict(obj)

    def get_owner_email(self, obj):
        return obj.owner.email if obj.owner_id else None

    def get_owner_username(self, obj):
        return obj.owner.username if obj.owner_id else None


class BusinessDetailCoreSerializer(BusinessSerializer):
    """
    Same as ``BusinessSerializer`` but without Crystal builder JSON (large columns).
    Pair with ``get_owned_business(..., defer_website_payload=True)`` on GET.
    """

    class Meta(BusinessSerializer.Meta):
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
            "logo",
            "subscriptions",
            "created_at",
            "updated_at",
        )


class BusinessListSerializer(BusinessDetailCoreSerializer):
    """
    Owner paginated list: same as ``BusinessDetailCoreSerializer`` plus ``logo_url``
    (from ``website_content.logo.src`` via DB annotation — no full ``website_content`` load).
    """

    logo_url = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()

    class Meta(BusinessDetailCoreSerializer.Meta):
        fields = (*BusinessDetailCoreSerializer.Meta.fields, "logo_url", "logo")

    def get_logo_url(self, obj) -> str:
        raw = getattr(obj, "_list_logo_url", None)
        if raw is None:
            return ""
        return str(raw).strip()

    def get_logo(self, obj) -> dict:
        key = (getattr(obj, "logo_s3_key", None) or "").strip()
        if key:
            by_key = self.context.get("gym_browser_url_by_s3_key")
            if isinstance(by_key, dict):
                url = (by_key.get(key) or "").strip()
                if url:
                    return {"type": "s3", "url": url, "s3_key": key}
            return business_logo_dict(obj)
        raw = getattr(obj, "_list_logo_url", None)
        if raw is not None and str(raw).strip():
            return {
                "type": "url",
                "url": str(raw).strip(),
                "s3_key": None,
            }
        return {"type": None, "url": "", "s3_key": None}


class BusinessPublicSerializer(serializers.ModelSerializer):
    """
    Public business profile (no owner identifiers). For gym pages / shareable links by slug.
    """

    logo = serializers.SerializerMethodField()
    website_theme = serializers.SerializerMethodField()
    website_content = serializers.SerializerMethodField()

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
            "logo",
            "website_theme",
            "website_content",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_website_theme(self, obj):
        p = getattr(obj, "website_payload", None)
        if p is None:
            return {}
        wt = p.website_theme
        return wt if isinstance(wt, dict) else {}

    def get_website_content(self, obj):
        return _website_content_dict(obj)

    def get_logo(self, obj):
        return business_logo_dict(obj)


class BusinessCreateSerializer(serializers.ModelSerializer):
    """For creating a business; owner is set in the view."""

    class Meta:
        model = Business
        fields = ("name", "slug", "description", "phone", "address", "location_map_url")

    def validate_slug(self, value):
        if Business.objects.filter(slug=value).exists():
            raise serializers.ValidationError("A business with this slug already exists.")
        return value

    def validate_phone(self, value):
        try:
            return normalize_phone_10_or_empty(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e)) from e


class BusinessUpdateSerializer(serializers.ModelSerializer):
    """Partial or full update of an owned business (PATCH)."""

    class Meta:
        model = Business
        fields = (
            "name",
            "slug",
            "description",
            "phone",
            "address",
            "location_map_url",
            "website_theme",
            "website_content",
        )

    def update(self, instance, validated_data):
        theme = validated_data.pop("website_theme", None)
        content = validated_data.pop("website_content", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if theme is not None or content is not None:
            payload, _ = BusinessWebsitePayload.objects.get_or_create(business=instance)
            if theme is not None:
                payload.website_theme = theme
            if content is not None:
                payload.website_content = content
            payload.save()
        return instance

    def validate_slug(self, value):
        qs = Business.objects.filter(slug=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A business with this slug already exists.")
        return value

    def validate_phone(self, value):
        try:
            return normalize_phone_10_or_empty(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e)) from e

    def validate_website_theme(self, value):
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("website_theme must be a JSON object.")
        return value

    def validate_website_content(self, value):
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("website_content must be a JSON object.")
        return value


class BusinessRecordStatusSerializer(serializers.Serializer):
    """POST body for soft delete / re-activate via record_status."""

    record_status = serializers.ChoiceField(choices=RECORD_STATUS_CHOICES)


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
                    raw = val or (
                        href[4:].strip() if href.lower().startswith("tel:") else ""
                    )
                    if raw:
                        try:
                            phone = normalize_phone_10(raw)
                        except ValueError:
                            phone = ""
                elif item_id == "address":
                    val = str(it.get("value") or "").strip()
                    if val:
                        address = val[:5000]

        return phone, address, location_map_url


MODAL_LEAD_TYPES = (
    CrystalLead.LEAD_JOIN_NOW,
    CrystalLead.LEAD_BOOK_FREE_TRIAL,
    CrystalLead.LEAD_PLAN_VISIT,
)

# Omitted from API payload — only used by management commands to purge seed rows.
_INTERNAL_LEAD_PAYLOAD_KEYS = frozenset({"seed_perfect_sample", "seed_owner_demo"})


class CrystalLeadModalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrystalLead
        fields = (
            "id",
            "lead_type",
            "payload",
            "quantity",
            "submitted_at_ms",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        p = data.get("payload")
        if isinstance(p, dict):
            cleaned = {k: v for k, v in p.items() if k not in _INTERNAL_LEAD_PAYLOAD_KEYS}
            if cleaned.get("seed") is True:
                cleaned = {k: v for k, v in cleaned.items() if k != "seed"}
            data["payload"] = cleaned
        return data


class CrystalLeadModalPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrystalLead
        fields = ("record_status",)


class BusinessEnquiryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessEnquiry
        fields = ("name", "email", "message")

    def validate_message(self, value: str) -> str:
        text = (value or "").strip()
        if len(text) < 3:
            raise serializers.ValidationError("Message is too short.")
        return text


class BusinessEnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessEnquiry
        fields = (
            "id",
            "business",
            "name",
            "email",
            "message",
            "enquiry_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "business", "created_at", "updated_at")


class BusinessEnquiryOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessEnquiry
        fields = (
            "id",
            "name",
            "email",
            "message",
            "enquiry_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class BusinessEnquiryPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessEnquiry
        fields = ("enquiry_status", "record_status")

