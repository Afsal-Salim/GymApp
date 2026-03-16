from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "username", "created_at")
    search_fields = ("email", "username")
