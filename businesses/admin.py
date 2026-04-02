from django.contrib import admin

from .models import Business, BusinessEnquiry, CrystalLead


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "created_at")
    search_fields = ("name", "slug", "owner__email")


@admin.register(BusinessEnquiry)
class BusinessEnquiryAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "name", "email", "enquiry_status", "created_at")
    list_filter = ("enquiry_status", "record_status", "created_at")
    search_fields = ("name", "email", "message", "business__slug")
    raw_id_fields = ("business",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(CrystalLead)
class CrystalLeadAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "lead_type", "quantity", "created_at")
    list_filter = ("lead_type", "created_at")
    search_fields = ("business__slug",)
    readonly_fields = ("created_at",)
