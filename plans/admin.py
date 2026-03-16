from django.contrib import admin

from .models import Feature, Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "currency", "duration")


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("name", "plan")
    list_filter = ("plan",)
