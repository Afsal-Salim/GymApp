from django.contrib import admin

from core.models import ClientSupportMessage, SiteEnquiry


@admin.register(SiteEnquiry)
class SiteEnquiryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "enquiry_kind",
        "phone",
        "enquiry_status",
        "record_status",
        "created_at",
    )
    list_filter = ("enquiry_kind", "enquiry_status", "record_status", "created_at")
    search_fields = ("name", "email", "phone", "service_topic", "message")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ClientSupportMessage)
class ClientSupportMessageAdmin(admin.ModelAdmin):
    list_display = (
        "kind",
        "customer",
        "subject",
        "support_status",
        "feedback_status",
        "record_status",
        "created_at",
    )
    list_filter = ("kind", "support_status", "feedback_status", "record_status", "created_at")
    search_fields = ("subject", "message", "customer__email", "customer__username")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("customer",)
