from django.contrib import admin

from core.models import ClientSupportMessage, SiteEnquiry


@admin.register(SiteEnquiry)
class SiteEnquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "email", "message")
    readonly_fields = ("created_at",)


@admin.register(ClientSupportMessage)
class ClientSupportMessageAdmin(admin.ModelAdmin):
    list_display = ("kind", "customer", "subject", "created_at")
    list_filter = ("kind", "created_at")
    search_fields = ("subject", "message", "customer__email", "customer__username")
    readonly_fields = ("created_at",)
    raw_id_fields = ("customer",)
